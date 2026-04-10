import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD_SCRIPT = PROJECT_ROOT / "scripts" / "plugins" / "create_plugin_scaffold.py"


class PluginSdkScaffoldTests(unittest.TestCase):
    def test_scaffold_creates_required_contract_files(self):
        with tempfile.TemporaryDirectory(prefix="mko-plugin-scaffold-") as tmpdir:
            out_dir = Path(tmpdir) / "demo_plugin"
            result = subprocess.run(
                [
                    "python",
                    str(SCAFFOLD_SCRIPT),
                    "--output-dir",
                    str(out_dir),
                    "--plugin-id",
                    "demo_plugin",
                    "--plugin-name",
                    "Demo Plugin",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Scaffold created at:", result.stdout)
            self.assertTrue((out_dir / ".mko-plugin" / "plugin.json").exists())
            self.assertTrue((out_dir / "plugin.py").exists())
            self.assertTrue((out_dir / "playbooks" / "dry_run_health_check.yml").exists())

            manifest = json.loads((out_dir / ".mko-plugin" / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["id"], "demo_plugin")
            self.assertEqual(manifest["mko_plugin_api"], "v1")


if __name__ == "__main__":
    unittest.main()
