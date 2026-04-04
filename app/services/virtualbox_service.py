"""VirtualBox inventory and adoption helpers."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Dict, List, Optional

from ..utils.config import ConfigManager


class VirtualBoxService:
    """Inspect host-side VirtualBox inventory for cluster adoption."""

    def __init__(self):
        self.config = ConfigManager()
        self.vboxmanage_binary = self.config.get("virtualbox.manage_binary", "VBoxManage")

    def _run(self, *args: str) -> str:
        """Run a VBoxManage command and return stdout."""
        command = [self.vboxmanage_binary, *args]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout

    def _parse_machine_readable(self, content: str) -> Dict[str, str]:
        """Parse VBoxManage --machinereadable output."""
        parsed: Dict[str, str] = {}
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key] = value.strip().strip('"')
        return parsed

    def _extract_guest_ips(self, vm_name: str) -> List[str]:
        """Extract guest IPs from VBox guest properties when available."""
        try:
            output = self._run("guestproperty", "enumerate", vm_name)
        except Exception:
            return []

        ips: List[str] = []
        for match in re.finditer(r"/VirtualBox/GuestInfo/Net/\d+/V4/IP\s+=\s+'([^']+)'", output):
            candidate = match.group(1).strip()
            if candidate and candidate != "127.0.0.1" and candidate not in ips:
                ips.append(candidate)
        return ips

    def _infer_role(self, vm_name: str, groups: List[str]) -> str:
        """Infer a likely cluster role from VM naming/grouping."""
        joined_groups = " ".join(groups).lower()
        lowered_name = vm_name.lower()
        if "server" in joined_groups or "control" in joined_groups or lowered_name.startswith("cp"):
            return "control-plane"
        if "worker" in joined_groups or lowered_name.startswith("wk"):
            return "worker"
        return "external-service"

    def _parse_groups(self, raw_groups: str) -> List[str]:
        """Parse VirtualBox group string into individual group names."""
        if not raw_groups:
            return []
        return [segment for segment in raw_groups.split("/") if segment]

    def list_vms(self, include_inaccessible: bool = False) -> List[Dict[str, Any]]:
        """List registered VirtualBox VMs with lightweight metadata."""
        output = self._run("list", "vms")
        vms: List[Dict[str, Any]] = []

        for line in output.splitlines():
            match = re.match(r'^"(?P<name>.*)" \{(?P<uuid>[^}]+)\}$', line.strip())
            if not match:
                continue

            vm_name = match.group("name")
            vm_uuid = match.group("uuid")
            if vm_name == "<inaccessible>" and not include_inaccessible:
                continue

            try:
                show_output = self._run("showvminfo", vm_name, "--machinereadable")
                info = self._parse_machine_readable(show_output)
            except Exception as exc:
                vms.append(
                    {
                        "name": vm_name,
                        "uuid": vm_uuid,
                        "accessible": False,
                        "error": str(exc),
                    }
                )
                continue

            groups = self._parse_groups(info.get("groups", ""))
            guest_ips = self._extract_guest_ips(vm_name)
            virtualization_role = self._infer_role(vm_name, groups)

            nics = []
            for nic_index in range(1, 5):
                nic_type = info.get(f"nic{nic_index}", "none")
                if nic_type == "none":
                    continue
                nics.append(
                    {
                        "index": nic_index,
                        "type": nic_type,
                        "bridge_adapter": info.get(f"bridgeadapter{nic_index}") or None,
                        "mac_address": info.get(f"macaddress{nic_index}") or None,
                    }
                )

            vms.append(
                {
                    "name": vm_name,
                    "uuid": vm_uuid,
                    "accessible": True,
                    "state": info.get("VMState", "unknown"),
                    "groups": groups,
                    "cpus": int(info.get("cpus", "0") or 0),
                    "memory_mb": int(info.get("memory", "0") or 0),
                    "guest_ips": guest_ips,
                    "management_ip_hint": guest_ips[0] if guest_ips else None,
                    "provider_vm_group": groups[-1] if groups else None,
                    "virtualization_provider": "virtualbox",
                    "inferred_role": virtualization_role,
                    "is_control_plane": virtualization_role == "control-plane",
                    "nics": nics,
                }
            )

        return vms

    def build_node_prefill(self, vm_name: str) -> Optional[Dict[str, Any]]:
        """Build prefill data for the add-node form from a VM name."""
        for vm in self.list_vms(include_inaccessible=False):
            if vm.get("name") != vm_name:
                continue
            return {
                "hostname": vm["name"],
                "ip_address": vm.get("management_ip_hint") or "",
                "ssh_user": self.config.get("ssh.default_user", "ubuntu"),
                "ssh_port": self.config.get("ssh.default_port", 22),
                "virtualization_provider": "virtualbox",
                "provider_vm_name": vm["name"],
                "provider_vm_group": vm.get("provider_vm_group") or "",
                "is_control_plane": vm.get("is_control_plane", False),
                "notes": (
                    f"Imported from VirtualBox inventory. "
                    f"State={vm.get('state', 'unknown')}; role={vm.get('inferred_role', 'unknown')}"
                ),
                "provider_metadata": json.dumps(
                    {
                        "uuid": vm.get("uuid"),
                        "groups": vm.get("groups", []),
                        "nics": vm.get("nics", []),
                        "guest_ips": vm.get("guest_ips", []),
                    }
                ),
            }
        return None
