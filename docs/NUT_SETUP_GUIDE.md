# NUT (Network UPS Tools) Setup Guide

This guide will help you set up NUT for UPS power management on your Raspberry Pi 5.

## Prerequisites

- Raspberry Pi 5 with Ubuntu/Debian
- UPS device connected via USB
- Root/sudo access

## Automatic Setup (Recommended)

The MicroK8s Cluster Orchestrator can automatically install and configure NUT:

```bash
# 1. Install NUT packages
python cli.py ups install-nut

# 2. Scan and configure UPS devices
python cli.py ups scan

# 3. Start NUT services
python cli.py ups services start

# 4. Check status
python cli.py ups services status
```

## Manual Setup

If you prefer manual setup or need to troubleshoot:

### 1. Install NUT Packages

```bash
sudo apt update
sudo apt install -y nut nut-client nut-server nut-driver
```

### 2. Configure NUT

The orchestrator will automatically generate these configuration files:

#### `/etc/nut/nut.conf`
```
MODE=standalone
```

#### `/etc/nut/ups.conf`
```
[aten3000]
	driver = nutdrv_qx
	port = auto
	vendorid = 0665
	productid = 5161
	desc = "ATEN 3000 Pro NJOY UPS"
```

#### `/etc/nut/upsd.users`
```
[admin]
	password = adminpass
	actions = SET
	instcmds = ALL
	upscmds = ALL

[monuser]
	password = monpass
	actions = GET
	instcmds = ALL
```

#### `/etc/nut/upsmon.conf`
```
MONITOR aten3000@localhost 1 monuser monpass primary
MINSUPPLIES 1
SHUTDOWNCMD "sudo shutdown -h now"
POLLFREQ 5
POLLFREQALERT 5
HOSTSYNC 15
DEADTIME 15
POWERDOWNFLAG /etc/nut/powerdown.flg
RBWARNTIME 45
NOCOMMWARNTIME 300
FINALDELAY 5
```

### 3. Start NUT Services

```bash
# Start services in order
sudo systemctl start nut-server
sudo systemctl start nut-driver
sudo systemctl start nut-client

# Enable services to start on boot
sudo systemctl enable nut-server
sudo systemctl enable nut-driver
sudo systemctl enable nut-client
```

### 4. Test UPS Connection

```bash
# Check if UPS is detected
upsc -l

# Get UPS status
upsc aten3000@localhost

# Test UPS commands
upscmd -l aten3000@localhost
```

## Troubleshooting

### UPS Not Detected

1. Check USB connection:
   ```bash
   lsusb | grep -i ups
   ```

2. Check NUT driver status:
   ```bash
   sudo systemctl status nut-driver
   sudo journalctl -u nut-driver -f
   ```

3. Try different drivers:
   ```bash
   # For ATEN UPS
   nut-scanner -U
   ```

### Permission Issues

1. Add user to nut group:
   ```bash
   sudo usermod -a -G nut $USER
   ```

2. Check file permissions:
   ```bash
   sudo chown nut:nut /etc/nut/*
   sudo chmod 640 /etc/nut/ups.conf
   sudo chmod 600 /etc/nut/upsd.users
   ```

### Service Issues

1. Check service status:
   ```bash
   sudo systemctl status nut-server
   sudo systemctl status nut-driver
   sudo systemctl status nut-client
   ```

2. View logs:
   ```bash
   sudo journalctl -u nut-server -f
   sudo journalctl -u nut-driver -f
   ```

3. Restart services:
   ```bash
   sudo systemctl restart nut-server
   sudo systemctl restart nut-driver
   ```

## Security Notes

- Change default passwords in `/etc/nut/upsd.users`
- Consider using more secure authentication methods
- Restrict network access if using network UPS sharing

## Integration with MicroK8s Cluster Orchestrator

Once NUT is configured, the orchestrator can:

1. **Monitor UPS status** in real-time
2. **Create power management rules** linking UPS to clusters
3. **Automatically shutdown clusters** on power loss
4. **Start clusters** when power is restored
5. **Scale cluster resources** based on battery level

### Example Power Management Rules

```bash
# Create rule to shutdown cluster on power loss
python cli.py ups rules create 1 1 power_loss graceful_shutdown \
  --name "Emergency Shutdown" \
  --description "Shutdown cluster when UPS goes on battery"

# Create rule to start cluster when power is restored
python cli.py ups rules create 1 1 power_restored startup \
  --name "Power Restored Startup" \
  --description "Start cluster when power is restored"

# Start power monitoring
python cli.py ups monitor start
```

## Web Interface

Access the UPS management interface at:
- URL: http://localhost:5000/ups
- Login: admin / admin123

Features:
- View UPS status and statistics
- Configure power management rules
- Monitor power events
- Manage NUT services

## Support

For issues with NUT configuration:
1. Check the logs: `sudo journalctl -u nut-*`
2. Verify UPS compatibility with NUT drivers
3. Test with `nut-scanner -U` and `upsc -l`
4. Consult NUT documentation: https://networkupstools.org/
