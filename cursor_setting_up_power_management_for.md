# Setting up power management for Aten 3000 Pro
_Exported on 9/27/2025 at 03:00:10 GMT+3 from Cursor (1.6.35)_

---

**User**

im trying to setup the power management of the aten 3000 pro njoy in this pc but not working trying using NUT. 

---

**Cursor**

Creating an initial checklist for NUT setup on the ATEN 3000 Pro NJOY. Checking the current system state.


NUT is installed but not configured. `MODE=none` in `/etc/nut/nut.conf`, and the services are inactive. The scanner detected a USB device but couldn’t access it due to permissions. Checking the UPS connection and configuring NUT for the ATEN 3000 Pro NJOY.


---

**User**


󰣇 sumix  ~   02:48  
 sudo nut-scanner -U
Scanning USB bus.
[nutdev-usb1]
	driver = "nutdrv_qx"	# alternately: blazer_usb
	port = "auto"
	vendorid = "0665"
	productid = "5161"
	# bus = "001"
	# device = "015"
	# busport = "001"

---

**Cursor**

UPS detected: ATEN 3000 Pro NJOY on USB. Vendor ID 0665, Product ID 5161. Driver: `nutdrv_qx` (alternatively `blazer_usb`). Configuring NUT for this UPS.


```properties
# Network UPS Tools: example ups.conf
#
# --- SECURITY NOTE ---
#
# If you use snmp-ups and set a community string in here, you
# will have to secure this file to keep other users from obtaining
# that string.  It needs to be readable by upsdrvctl and any drivers,
# and by upsd.
#
# ---
#
# NOTE: Contents of this file should be pure ASCII (character codes
# not in range would be ignored with a warning message).
#
# This is where you configure all the UPSes that this system will be
# monitoring directly.  These are usually attached to serial ports, but
# USB devices and SNMP devices are also supported.
#
# This file is used by upsdrvctl to start and stop your driver(s), and
# is also used by upsd to determine which drivers to monitor.  The
# drivers themselves also read this file for configuration directives.
#
# The general form is:
#
# [upsname]
#       driver = <drivername>
#         port = <portname>
#       < any other directives here >
#
# The section header ([upsname]) can be just about anything as long as
# it is a single word inside brackets.  upsd uses this to uniquely
# identify a UPS on this system.
#
# If you have a UPS called snoopy, your section header would be "[snoopy]".
# On a system called "doghouse", the line in your upsmon.conf to monitor
# and manage it would look something like this:
#
#   MONITOR snoopy@doghouse 1 monuser mypassword primary
#
# It might look like this if monitoring in "secondary" mode (without any
# ability to directly manage the UPS) from a different system:
#
#   MONITOR snoopy@doghouse 1 monuser mypassword secondary
#
# Configuration directives
# ------------------------
#
# These directives are used by upsdrvctl only and should be specified outside
# of a driver definition:
#
#      chroot: OPTIONAL. Used for securing. See man page for details.
#
#  driverpath: OPTIONAL. Used for custom setups. See man page for details.
#
#   statepath: OPTIONAL. Used for custom setups. Tell drivers to place their
#              state sockets for communication with 'upsd' in 'path' rather
#              than the default location that was compiled into the program.
#              Note that the drivers must use the same path as 'upsd', so the
#              data server would prefer this setting from `ups.conf` global
#              section, if present, over its own in `upsd.conf`.
#              Environment variable NUT_STATEPATH set by caller can override
#              this setting.
#
#      nowait: OPTIONAL. Tell upsdrvctl to not wait at all for the driver(s)
#              to execute the requested command. Fire and forget.
#
# pollinterval: OPTIONAL. The status of the UPS will be refreshed after a
#              maximum delay which is controlled by this setting (default
#              2 seconds). This may be useful if the driver is creating too
#              much of a load on your system or network.
#              Note that some drivers also have an option called *pollfreq*
#              which controls how frequently some of the less critical
#              parameters are polled. See respective driver man pages.
#

# Set maxretry to 3 by default, this should mitigate race with slow devices:
maxretry = 3

# These directives can be set outside and inside a driver definition,
# sometimes with slightly different meanings per context:
#
#    maxretry: OPTIONAL.  Specify the number of attempts to start the driver(s),
#              in case of failure, before giving up. A delay of 'retrydelay' is
#              inserted between each attempt. Caution should be taken when using
#              this option, since it can impact the time taken by your system to
#              start.
#
#              The built-in default is 1 attempt.
#
#  retrydelay: OPTIONAL.  Specify the delay between each restart attempt of the
#              driver(s), as specified by 'maxretry'. Caution should be taken
#              when using this option, since it can impact the time taken by your
#              system to start.
#
#              The default is 5 seconds.
#
# maxstartdelay: OPTIONAL.  This can be set as a global variable
#                above your first UPS definition and it can also be
#                set in a UPS section.  This value controls how long
#                upsdrvctl will wait for the driver to finish starting.
#                This keeps your system from getting stuck due to a
#                broken driver or UPS.
#                Note that after this time upsdrvctl would just move
#                along with its business (whether retrying the same
#                driver if `maxretry>1`, or trying another driver if
#                starting them all, or just eventually exit); however,
#                each such most recently started "stuck" driver process
#                may be further initializing in the background, and
#                might even succeed eventually.
#                They would not be actively killed by upsdrvctl after
#                this timeout expires.
#
#                The default is 75 seconds.
#
#   debug_min: OPTIONAL.  Specify a minimum debug level for all driver daemons
#              (when specified at global level), or for this driver daemon
#              (when specified in a driver section), e.g. for troubleshooting
#              a deployment. This does not directly impact the foreground or
#              background running mode. If both the global and driver level
#              `debug_min` are set, the driver-level setting takes precedence.
#              Command-line option `-D` can only increase this verbosity level.
#
# LIBUSB_DEBUG: OPTIONAL.  For run-time troubleshooting of USB-capable NUT
#                drivers, you can specify the verbosity of LibUSB specific
#                debugging as a numeric value such as `4` ("All messages
#                are emitted").  Should not have any practical impact on
#                other NUT drivers. For more details, see the library's
#                documentation at e.g. https://libusb.sourceforge.io/api-1.0/
#
# user, group: OPTIONAL. Overrides the compiled-in (also global-section,
#                when used in driver section) default unprivileged user/group
#                name for NUT device driver. Impacts access rights used for
#                the socket file access (group) and communication ports (user).
#
# synchronous: OPTIONAL.  The driver work by default in asynchronous
#              mode (like *no*) with fallback to synchronous if sending
#              fails (i.e *synchronous=auto*).  This means that all data
#              are pushed by the driver on the communication socket to
#              upsd (Unix socket on Unix, Named pipe on Windows) without
#              waiting for these data to be actually consumed.  With
#              some HW, such as ePDUs, that can produce a lot of data,
#              asynchronous mode may cause some congestion, resulting in
#              the socket to be full, and the driver to appear as not
#              connected.  By enabling the 'synchronous' flag
#              (value = 'yes'), the driver will wait for data to be
#              consumed by upsd, prior to publishing more.  This can be
#              enabled either globally or per driver.
#
#              The default is 'no' (i.e. asynchronous mode) for backward
#              compatibility of the driver behavior.
#

# These directives are common to all drivers that support ups.conf:
#
#  driver: REQUIRED.  Specify the program to run to talk to this UPS.
#          apcsmart, bestups, and sec are some examples.
#
#    port: REQUIRED.  The serial port where your UPS is connected.
#          For example:
#            /dev/ttyS0 is usually the first port on Linux boxes.
#            "\\\\.\\COM1" is the first port on Windows boxes (note that
#                the backslash characters themselves must be escaped,
#                for the NUT configuration parser to yield "\\.\COM1").
#
# sdorder: OPTIONAL.  When you have multiple UPSes on your system, you
#          usually need to turn them off in a certain order.  upsdrvctl
#          shuts down all the 0s, then the 1s, 2s, and so on.  To exclude
#          a UPS from the shutdown sequence, set this to -1.
#
#          The default value for this parameter is 0.
#
# sdcommands: OPTIONAL.  Comma-separated list of instant command name(s)
#          to send to the UPS when you request its shutdown.  For more
#          details about relevant use-cases see the ups.conf manual page.
#
#          The default value is built into each driver (where supported).
#
#    desc: optional, to keep a note of the UPS purpose, location, etc.
#
#  nolock: optional, and not recommended for use in this file.
#
#          If you put nolock in here, the driver will not lock the
#          serial port every time it starts.  This may allow other
#          processes to seize the port if you start more than one by
#          mistake.
#
#          This is only intended to be used on systems where locking
#          absolutely must be disabled for the software to work.
#
# ignorelb: OPTIONAL. Ignore low battery condition reported by device,
#           and evaluate remaining battery charge or runtime instead.
#           See man page for details.
#
# usb_set_altinterface(=num): OPTIONAL. Require that NUT calls this method
#           to set the interface, even if 0 (default). Some devices require
#           the call to initialize; others however can get stuck due to it -
#           so it is not called by default. Yet others can be composite
#           devices which use a non-zero interface to represent the UPS.
#
# usb_config_index=hexnum, usb_hid_rep_index=hexnum,
# usb_hid_desc_index=hexnum, usb_hid_ep_in=hexnum, usb_hid_ep_out=hexnum:
#           OPTIONAL. Force use of specific interface, endpoint, descriptor
#           index etc. numbers, rather than defaulting to 0 (rarely other
#           values in certain drivers for some devices known to use non-zero
#           numbers). As a rule of thumb for `usb_hid_desc_index` discovery,
#           you can see larger `wDescriptorLength` values (roughly 600+ bytes)
#           in reports of `lsusb` or similar tools.
#
# default.<variable>: OPTIONAL. Set a default value for <variable> which is
#           used in case the UPS doesn't provide a value, but which will be
#           overwritten if a value is available from the UPS, e.g.:
#               default.input.voltage.nominal = 230
#           will report the nominal input voltage to be 230, unless the UPS
#           eventually tells us differently.
#
# override.<variable>: OPTIONAL. Set a value for <value> that overrides
#           (for NUT) any value that may be read from the UPS.
#           Used for overriding values from the UPS that are clearly wrong
#           (e.g. some devices report wrong values for battery voltage):
#               override.battery.voltage.nominal = 12
#           Use with caution!  This will only change the appearance of the
#           variable to the outside world (and NUT calculations), internally
#           in the UPS the original value is used.
#
# Anything else is passed through to the hardware-specific part of
# the driver.
#
# Examples
# --------
#
# A simple example for a UPS called "powerpal" that uses the blazer_ser
# driver on /dev/ttyS0 is:
#
# [powerpal]
#   driver = blazer_ser
#   port = /dev/ttyS0
#   desc = "Web server"
#
# If your UPS driver requires additional settings, you can specify them
# here.  For example, if it supports a setting of "1234" for the
# variable "cable", it would look like this:
#
# [myups]
#   driver = mydriver
#   port = /dev/ttyS1
#   cable = 1234
#   desc = "Something descriptive"
#
# To find out if your driver supports any extra settings, start it with
# the -h option and/or read the driver's documentation.

# ATEN 3000 Pro NJOY UPS Configuration
[aten3000]
	driver = nutdrv_qx
	port = auto
	vendorid = 0665
	productid = 5161
	desc = "ATEN 3000 Pro NJOY UPS"

```

```properties
# Network UPS Tools: example nut.conf
#
# This file tries to standardize the various files being found in the field,
# like /etc/default/nut on Debian based systems, /etc/sysconfig/ups on RedHat
# based systems, ... Distribution's init script or service unit/method script
# should source this file to see which component(s) has to be started.
# Some scripts and units provided by NUT project itself may also look into
# this file for optional configuration about OS integration.
#
# IMPORTANT NOTES:
#  This file is intended to be sourced by standard POSIX shell scripts
#  (so there is no guaranteed `export VAR=VAL` syntax, while you may need
#  to `export VAR` when sourcing it into init-scripts, for propagation to
#  NUT programs eventually), and additionally by systemd on Linux (with no
#  guaranteed expansion of variables -- only verbatim assignments).
#
#  You MUST NOT use spaces around the equal sign!
#
#  Practical support for this file and its settings currently varies between
#  various OS packages and NUT sample scripts, but should converge over time.
#
#  Contents of this file should be pure ASCII (character codes not in range
#  would be ignored with a warning message).
#
# See also: `man nut.conf` (usually in Manual pages Section 5,
#           for Configuration files)
#
##############################################################################
# General section
##############################################################################
# The MODE determines which part of the NUT is to be started, and which
# configuration files must be modified.
#
# The values of MODE can be:
# - none: NUT is not configured, or use the Integrated Power Management, or use
#   some external system to startup NUT components. So nothing is to be started
#   by scripts or services bundled with NUT packages.
# - standalone: This mode address a local only configuration, with 1 UPS
#   protecting the local system. This implies to start the 3 NUT layers (driver,
#   upsd and upsmon) and the matching configuration files. This mode can also
#   address UPS redundancy.
# - netserver: same as for the standalone configuration, but also need
#   some more network access controls (firewall, tcp-wrappers) and possibly a
#   specific LISTEN directive in upsd.conf.
#   Since this MODE is opened to the network, a special care should be applied
#   to security concerns.
# - netclient: this mode only requires upsmon (and tools it may be using, like
#   upssched or custom scripts) to monitor a remote NUT server and possibly
#   shut down this system (part of upsmon must run as root then).

MODE=standalone

# Uncomment this to allow starting the `upsd` data server even if `ups.conf`
# has no device sections configured at the moment. This environment variable
# overrides the built-in "false" flag in `upsd`, and an optional same-named
# default flag that can be set in `upsd.conf`. If you want a data server always
# running, even if it initially has nothing to serve (may be live-reloaded
# later, when devices become configured), this option is for you.
#ALLOW_NO_DEVICE=true
#export ALLOW_NO_DEVICE

# Uncomment this to allow starting the `upsd` data server even if not all
# `LISTEN` directives can be honoured at the moment. This environment variable
# overrides the built-in "false" flag in `upsd`, and an optional same-named
# default flag that can be set in `upsd.conf`. If you want a data server always
# running, even if it would potentially not serve all clients on every uptime,
# this option is for you (note you would have to restart `upsd` to pick up the
# `LISTEN`ed IP address if it appears later). Probably `LISTEN *` is better.
#ALLOW_NOT_ALL_LISTENERS=true
#export ALLOW_NOT_ALL_LISTENERS

# The optional 'UPSD_OPTIONS' allow to set upsd specific command-line options.
# It is ignored when 'MODE' above indicates that no upsd should be running.
# It may be redundant in comparison to options which can be set in `upsd.conf`.
#UPSD_OPTIONS=

# The optional 'UPSMON_OPTIONS' allow to set upsmon specific command-line options.
# It is ignored when 'MODE' above indicates that no upsmon should be running.
# It may be redundant in comparison to options which can be set in `upsmon.conf`.
#UPSMON_OPTIONS=

# If the optional 'POWEROFF_WAIT' is configured (to a value that can be handled
# by `/bin/sleep` on the current system - typically an integer with the number
# of seconds for a delay, but not always limited to that syntax), and the current
# system which manages one or more UPS devices would not only command it to shut
# down, but also try to avoid the "Power race". Caveats emptor, see NUT FAQ and
# other docs for details.
#POWEROFF_WAIT=3600

# The optional 'POWEROFF_QUIET' setting controls if the NUT shutdown integration
# scripts or service units would emit messages about their activity (or lack
# thereof). By default they may be verbose, to aid post-mortem troubleshooting
# via logs or console captures.
# Set to `true` to avoid that trove of information, if you consider it noise.
#POWEROFF_QUIET=true

# The optional 'NUT_DEBUG_LEVEL' setting controls the default debugging message
# verbosity passed to NUT daemons. As an environment variable, its priority sits
# between that of 'DEBUG_MIN' setting of a driver and the command-line options.
#NUT_DEBUG_LEVEL=0
#export NUT_DEBUG_LEVEL

# Optionally add current process ID to tags with debug-level identifiers.
# This may be useful when many NUT daemons write to the same console or log
# file, such as in containers/plugins for Home Assistant, storage appliances...
#NUT_DEBUG_PID=true
#export NUT_DEBUG_PID

# Normally NUT can (attempt to) use the syslog or Event Log (WIN32), but the
# environment variable 'NUT_DEBUG_SYSLOG' allows to bypass it, and perhaps keep
# the daemons logging to stderr (useful e.g. in NUT Integration Test suite to
# not pollute the OS logs, or in systemd where stderr and syslog both go into
# the same journal). Recognized values:
#  `stderr`  Disabled and background() keeps stderr attached
#  `none`    Disabled and background() detaches stderr as usual
#  `default`/unset/other   Not disabled
#NUT_DEBUG_SYSLOG=stderr
#export NUT_DEBUG_SYSLOG

# Normally NUT can (attempt to) verify that the program file name matches the
# name associated with a running process, when using PID files to send signals.
# The `NUT_IGNORE_CHECKPROCNAME` boolean toggle allows to quickly skip such
# verification, in case it causes problems (e.g. NUT programs were renamed and
# do not match built-in expectations). This environment variable can also be
# optionally set in init-scripts or service methods for `upsd`, `upsmon` and
# NUT drivers/`upsdrvctl`.
#NUT_IGNORE_CHECKPROCNAME=true
#export NUT_IGNORE_CHECKPROCNAME

# Optional flag to prevent daemons which can notify service management frameworks
# (such as systemd) about passing their lifecycle milestones, to not report
# loudly if they could NOT do so (e.g. running on a system without a framework,
# or misconfigured so they could not report and the OS could eventually restart
# the false-positively identified "unresponsive" service.
# Currently such reports, done by default, help troubleshoot service start-up
# and highlight that NUT sources (or package build) did not take advantage of
# tighter OS service management framework integration (if one exists, so that
# developers could focus on adding that). Reasons to set this flag could include
# platforms without such a framework and not expecting one, although nagging
# your favourite OS or contributing development to make it better is also a way.
#NUT_QUIET_INIT_UPSNOTIFY=true
#export NUT_QUIET_INIT_UPSNOTIFY

##############################################################################
# Variables that can be helpful more for tool scripting than service daemons
##############################################################################

# Optionally prevent `libupsclient` consumers (notoriously `upsc`, maybe
# also `dummy-ups` driver or `nut-scanner` tool) from reporting whether
# they have initialized SSL support -- or, loudly, failed to initialize
# as it was not configured on this system.
#NUT_QUIET_INIT_SSL=true
#export NUT_QUIET_INIT_SSL

# Optionally suppress NUT tool name and version banner (normally shown in most
# NUT programs unilaterally, before processing any CLI options and possibly
# failing due to that).
# NOT recommended for services due to adverse troubleshooting impact, but may
# be helpful in shell profiles or scripts which process NUT tool outputs.
#NUT_QUIET_INIT_BANNER=true
#export NUT_QUIET_INIT_BANNER

# Optionally suppress reporting of sockets the driver programs listen at.
#NUT_QUIET_INIT_LISTENER=true
#export NUT_QUIET_INIT_LISTENER

# Optionally impose a connection timeout for NUT client programs. The built-in
# default is "0" meaning indefinitely blocking attempts, but many NUT clients
# since NUT v2.8.3 set it to "10" by their default (can be overridden by this
# variable, or via command line or configuration for some of them).
#NUT_DEFAULT_CONNECT_TIMEOUT=10
#export NUT_DEFAULT_CONNECT_TIMEOUT

```

---

**User**

 sudo cat /etc/nut/upsd.users
# Network UPS Tools: Example upsd.users
#
# This file sets the permissions for upsd - the UPS network daemon.
# Users are defined here, are given passwords, and their privileges are
# controlled here too.  Since this file will contain passwords, keep it
# secure, with only enough permissions for upsd to read it.
#
# NOTE: Contents of this file should be pure ASCII (character codes
# not in range would be ignored with a warning message).

# --------------------------------------------------------------------------

# Each user gets a section.  To start a section, put the username in
# brackets on a line by itself.  To set something for that user, specify
# it under that section heading.  The username is case-sensitive, so
# admin and AdMiN are two different users.
#
# Possible settings:
#
# password: The user's password.  This is case-sensitive.
#
# --------------------------------------------------------------------------
#
# actions: Let the user do certain things with upsd.
#
# Valid actions are:
#
# SET   - change the value of certain variables in the UPS
# FSD   - set the "forced shutdown" flag in the UPS
#
# --------------------------------------------------------------------------
#
# instcmds: Let the user initiate specific instant commands.  Use "ALL"
# to grant all commands automatically.  There are many possible
# commands, so use 'upscmd -l' to see what your hardware supports.  Here
# are a few examples:
#
# test.panel.start      - Start a front panel test
# test.battery.start    - Start battery test
# test.battery.stop     - Stop battery test
# calibrate.start       - Start calibration
# calibrate.stop        - Stop calibration
#
# --------------------------------------------------------------------------
#
# Example:
#
#	[admin]
#		password = mypass
#		actions = SET
#		instcmds = ALL
#

#
# --- Configuring for a user who can execute tests only
#
#	[testuser]
#		password  = pass
#		instcmds  = test.battery.start
#		instcmds  = test.battery.stop

#
# --- Configuring for upsmon
#
# To add a NUT user for your upsmon, with a particular role, use this example:
#
#   [monuser]
#       password  = pass
#       upsmon primary
# or
#       upsmon secondary
#
# The matching MONITOR line in your upsmon.conf would look like this:
#
# MONITOR myups@localhost 1 monuser pass primary	(or secondary)
#
# See comments in the upsmon.conf(.sample) file for details about this
# keyword and the difference of NUT secondary and primary systems.

󰣇 sumix  ~   02:52  
 

---

**Cursor**

Configuring NUT users and starting services to test UPS communication.


```plaintext
# See comments in the upsmon.conf(.sample) file for details about this
# keyword and the difference of NUT secondary and primary systems.

# Admin user for UPS management
[admin]
	password = adminpass
	actions = SET
	instcmds = ALL

# Monitor user for upsmon
[monuser]
	password = monpass
	upsmon primary
```

NUT is configured for the ATEN 3000 Pro NJOY. Next steps:

## Configuration Summary

1. **UPS Configuration** (`/etc/nut/ups.conf`):
   - Added `aten3000` entry with `nutdrv_qx` driver
   - Set vendor ID `0665` and product ID `5161`
   - Port set to `auto` for USB detection

2. **NUT Mode** (`/etc/nut/nut.conf`):
   - Changed from `MODE=none` to `MODE=standalone`

3. **User Configuration** (`/etc/nut/upsd.users`):
   - Add an admin user and a monitor user

## Next Steps

Run these commands to complete the setup:

```bash
# Add users to upsd.users
sudo tee -a /etc/nut/upsd.users << 'EOF'

# Admin user for UPS management
[admin]
	password = adminpass
	actions = SET
	instcmds = ALL

# Monitor user for upsmon
[monuser]
	password = monpass
	upsmon primary
EOF

# Start NUT services
sudo systemctl start nut-server
sudo systemctl start nut-monitor

# Enable services to start on boot
sudo systemctl enable nut-server
sudo systemctl enable nut-monitor

# Test UPS communication
upsc aten3000@localhost
```

## Testing Commands

After starting the services, you can test with:

```bash
# Check UPS status
upsc aten3000@localhost

# List all UPS variables
upsc -l aten3000@localhost

# Check if UPS is online
upsc aten3000@localhost ups.status

# Test UPS communication
upscmd -l aten3000@localhost
```

## Troubleshooting

If you encounter issues:

1. Check service status: `sudo systemctl status nut-server nut-monitor`
2. Check logs: `sudo journalctl -u nut-server -f`
3. Test driver manually: `sudo /lib/nut/nutdrv_qx -a aten3000 -DDD`

Should I continue with the user configuration and service startup?

```shellscript
# Add users to upsd.users
sudo tee -a /etc/nut/upsd.users << 'EOF'

# Admin user for UPS management
[admin]
	password = adminpass
	actions = SET
	instcmds = ALL

# Monitor user for upsmon
[monuser]
	password = monpass
	upsmon primary
EOF

# Start NUT services
sudo systemctl start nut-server
sudo systemctl start nut-monitor

# Enable services to start on boot
sudo systemctl enable nut-server
sudo systemctl enable nut-monitor

# Test UPS communication
upsc aten3000@localhost
```

```shellscript
# Check UPS status
upsc aten3000@localhost

# List all UPS variables
upsc -l aten3000@localhost

# Check if UPS is online
upsc aten3000@localhost ups.status

# Test UPS communication
upscmd -l aten3000@localhost
```

---

**User**

󰣇 sumix  ~   02:53  
 sudo systemctl start nut-server

󰣇 sumix  ~   02:53  
 upsc aten3000@localhost
Error: Driver not connected

󰣇 sumix  ~   02:54  
 upsc -l aten3000@localhost
upscli_splitaddr: wrong call? Got upsname@hostname[:port] string where only hostname[:port] was expected: aten3000@localhost

upscli_tryconnect: Host not found: 'aten3000@localhost'
Error: No such host

󰣇 sumix  ~   02:54  
 

󰣇 sumix  ~   02:54  
 upscmd -l aten3000@localhost
Error: Driver not connected

󰣇 sumix  ~   02:54  
 

---

**Cursor**

Driver isn't connected. Checking service status and starting the driver.


---

**User**

󰣇 sumix  ~   02:54  
 sudo systemctl status nut-server
● nut-server.service - Network UPS Tools - power devices information server
     Loaded: loaded (/usr/lib/systemd/system/nut-server.service; disabled; preset: disabled)
     Active: active (running) since Sat 2025-09-27 02:53:43 EEST; 1min 11s ago
 Invocation: aed0029d7a33481e8f148e9452846466
       Docs: man:upsd(8)
             https://www.networkupstools.org/historic/v2.8.4/docs/man/upsd.html
             man:ups.conf(5)
             https://www.networkupstools.org/historic/v2.8.4/docs/man/ups.conf.html
             man:upsd.conf(5)
             https://www.networkupstools.org/historic/v2.8.4/docs/man/upsd.conf.html
             man:upsd.users(5)
             https://www.networkupstools.org/historic/v2.8.4/docs/man/upsd.users.html
             man:nut.conf(5)
             https://www.networkupstools.org/historic/v2.8.4/docs/man/nut.conf.html
    Process: 92733 ExecStartPre=/usr/bin/systemd-tmpfiles --create /usr/lib/tmpfiles.d/nut-common-tmpfiles.conf (code=exited, status=0/SUCCESS)
    Process: 92736 ExecStartPost=/bin/grep -E Units|Max open files /proc/${MAINPID}/limits (code=exited, status=0/SUCCESS)
   Main PID: 92735 (upsd)
      Tasks: 1 (limit: 76701)
     Memory: 1.4M (peak: 3.7M)
        CPU: 43ms
     CGroup: /system.slice/nut-server.service
             └─92735 /usr/bin/upsd -F

Sep 27 02:53:43 sumix-d nut-server[92736]: Max open files            1048576              1048576              files
Sep 27 02:53:43 sumix-d upsd[92735]: Running as foreground process, not saving a PID file
Sep 27 02:53:43 sumix-d nut-server[92735]: Running as foreground process, not saving a PID file
Sep 27 02:53:43 sumix-d nut-server[92735]: upsnotify: notify about state NOTIFY_STATE_READY_WITH_PID with libsystemd: was requested, but not running as a service unit now, will not spam more about it
Sep 27 02:53:43 sumix-d nut-server[92735]: upsnotify: failed to notify about state NOTIFY_STATE_READY_WITH_PID: no notification tech defined, will not spam more about it
Sep 27 02:53:43 sumix-d nut-server[92735]: upsnotify: logged the systemd watchdog situation once, will not spam more about it
Sep 27 02:53:43 sumix-d systemd[1]: Started Network UPS Tools - power devices information server.
Sep 27 02:53:43 sumix-d upsd[92735]: upsnotify: notify about state NOTIFY_STATE_READY_WITH_PID with libsystemd: was requested, but not running as a service unit now, will not spam more about it
Sep 27 02:53:43 sumix-d upsd[92735]: upsnotify: failed to notify about state NOTIFY_STATE_READY_WITH_PID: no notification tech defined, will not spam more about it
Sep 27 02:53:43 sumix-d upsd[92735]: upsnotify: logged the systemd watchdog situation once, will not spam more about it

---

**Cursor**

nut-server is running, but the UPS driver isn’t started. In standalone mode, we need to start the driver separately. Starting the driver:


Start the UPS driver:

```bash
sudo upsdrvctl start
```

This should start the `nutdrv_qx` driver for the ATEN 3000 Pro NJOY. After it starts, test the connection:

```bash
# Check if the driver is running
ps aux | grep nutdrv_qx

# Test UPS communication
upsc aten3000@localhost

# List available UPS variables
upsc -l aten3000@localhost
```

If the driver starts successfully, you should see output like:
- `battery.charge`
- `battery.voltage`
- `input.voltage`
- `ups.status`
- `ups.load`

If you get errors, check the driver logs:

```bash
# Check driver logs
sudo journalctl -u nut-driver@aten3000 -f

# Or check system logs for NUT
sudo journalctl | grep -i nut
```

Start the driver and share the output.

```shellscript
sudo upsdrvctl start
```

```shellscript
# Check if the driver is running
ps aux | grep nutdrv_qx

# Test UPS communication
upsc aten3000@localhost

# List available UPS variables
upsc -l aten3000@localhost
```

```shellscript
# Check driver logs
sudo journalctl -u nut-driver@aten3000 -f

# Or check system logs for NUT
sudo journalctl | grep -i nut
```

---

**User**

󰣇 sumix  ~   02:54  
 sudo upsdrvctl start
Network UPS Tools upsdrvctl - UPS driver controller 2.8.4 release
Network UPS Tools 2.8.4 release - Generic Q* USB/Serial driver 0.45
USB communication driver (libusb 1.0) 0.50
Using protocol: Voltronic 0.12
battery_number: 6
battery_number, settable range: 1..9
bypass_alarm: enabled
battery_alarm: enabled
bypass_when_off: disabled
alarm_control: enabled
converter_mode: disabled
eco_mode: disabled
bypass_forbidding: disabled
max_bypass_volt: 264
max_bypass_volt, settable range: 230..264
min_bypass_volt: 180
min_bypass_volt, settable range: 170..220
max_bypass_freq: 53.0
max_bypass_freq, settable range: 51.0..60.0
min_bypass_freq: 47.0
min_bypass_freq, settable range: 40.0..49.0
No values for battery high/low voltages
Using 'guesstimation' (low: 62.400000, high: 78.000000)!
Listening on socket /var/lib/nut/nutdrv_qx-aten3000
WARNING: upsdrvctl was called directly on a system with systemd support.
    Please consider using 'upsdrvsvcctl' instead, to avoid conflicts with
    nut-driver service instances prepared by 'nut-driver-enumerator'!

󰣇 sumix  ~   02:55  
 

---

**Cursor**

Driver is running and connected to the UPS. Testing communication:


UPS is connected and reporting data. Setting up monitoring and shutdown procedures.


UPS is connected and reporting data. Status: OL (Online). Battery: 99% (82.1 V), runtime ~54 min. Load: 15% (450 W of 3000 W). Input: 233.5 V, 50 Hz. Output: 229.5 V, 50 Hz. Temperature: 23.5°C.

Setting up monitoring and shutdown procedures.


## ATEN 3000 Pro NJOY is configured and working

### Current status
- **UPS status**: Online (OL)
- **Battery**: 99% (82.1V)
- **Runtime**: ~54 minutes
- **Load**: 15% (450W of 3000W)
- **Input**: 233.5V, 50Hz
- **Output**: 229.5V, 50Hz
- **Temperature**: 23.5°C

### Next steps for monitoring and shutdown

1. **Add users to upsd.users**:
```bash
sudo tee -a /etc/nut/upsd.users << 'EOF'

# Admin user for UPS management
[admin]
	password = adminpass
	actions = SET
	instcmds = ALL

# Monitor user for upsmon
[monuser]
	password = monpass
	upsmon primary
EOF
```

2. **Configure upsmon for monitoring**:
```bash
# Edit /etc/nut/upsmon.conf and add:
MONITOR aten3000@localhost 1 monuser monpass primary
```

3. **Start monitoring service**:
```bash
sudo systemctl start nut-monitor
sudo systemctl enable nut-monitor
```

4. **Enable services on boot**:
```bash
sudo systemctl enable nut-server
sudo systemctl enable nut-driver@aten3000
```

### Useful commands
```bash
# Check UPS status
upsc aten3000@localhost

# Check specific values
upsc aten3000@localhost battery.charge
upsc aten3000@localhost ups.status
upsc aten3000@localhost battery.runtime

# Test UPS commands
upscmd -l aten3000@localhost

# Check service status
sudo systemctl status nut-server nut-monitor
```

### Power management features
- Automatic shutdown on low battery
- Graceful shutdown before UPS battery depletes
- Monitoring of power conditions
- Email notifications (if configured)

The UPS is communicating with NUT and ready for power management.

```shellscript
sudo tee -a /etc/nut/upsd.users << 'EOF'

# Admin user for UPS management
[admin]
	password = adminpass
	actions = SET
	instcmds = ALL

# Monitor user for upsmon
[monuser]
	password = monpass
	upsmon primary
EOF
```

```shellscript
# Edit /etc/nut/upsmon.conf and add:
MONITOR aten3000@localhost 1 monuser monpass primary
```

```shellscript
sudo systemctl start nut-monitor
sudo systemctl enable nut-monitor
```

```shellscript
sudo systemctl enable nut-server
sudo systemctl enable nut-driver@aten3000
```

```shellscript
# Check UPS status
upsc aten3000@localhost

# Check specific values
upsc aten3000@localhost battery.charge
upsc aten3000@localhost ups.status
upsc aten3000@localhost battery.runtime

# Test UPS commands
upscmd -l aten3000@localhost

# Check service status
sudo systemctl status nut-server nut-monitor
```

---

**User**

󰣇 sumix  ~   02:57  
 sudo grep -A 5 -B 5 "MONITOR" /etc/nut/upsmon.conf
# This file contains passwords, so keep it secure.
#
# NOTE: Contents of this file should be pure ASCII (character codes
# not in range would be ignored with a warning message).
#
# A minimal configuration should include at least one MONITOR instruction,
# MINSUPPLIES (may be 0 if this system is only monitoring other NUT servers),
# and a POWERDOWNFLAG if this machine is a "primary" system connected to
# the UPS and drives its late-shutdown power-off command in an emergency.
# You should also define a SHUTDOWNCMD (like the example below, or something
# special for your deployment) if MINSUPPLIES is at least 1 and you MONITOR
# an UPS. A NOTIFYCMD integrating with `upssched` is a common situation too.

# --------------------------------------------------------------------------
# RUN_AS_USER <userid>
#
--
#
# (Unprivileged) OS account to run as:
# RUN_AS_USER nut

# --------------------------------------------------------------------------
# MONITOR <system> <powervalue> <username> <password> ("primary"|"secondary")
#
# List systems you want to monitor.  Not all of these may supply power
# to the system running upsmon, but if you want to watch it, it has to
# be in this section.
#
--
# feeds on this system.  Most personal computers only have one power supply,
# so this value is normally set to 1, while most modern servers have at least
# two.  You need a pretty big or special box to have any other value here.
#
# You can also set this to 0 for a system that doesn't take any power
# from the MONITORed supply, which you still want to monitor (e.g. for an
# administrative workstation fed from a different circuit than the datacenter
# servers it monitors). Use <powervalue> if 0 when you want to hear about
# changes for a given UPS without shutting down when it goes critical.
#
# <username> and <password> must match an entry in that system's
--
# would better go down after all its clients). You would be well served by
# higher-end UPSes with manageable thresholds to declare a critical state.
#
# Examples:
#
# MONITOR myups@bigserver 1 upswired blah primary
# MONITOR su700@server.example.com 1 monuser secretpass secondary
# MONITOR myups@localhost 1 monuser pass primary	# (or secondary)

# --------------------------------------------------------------------------
# MINSUPPLIES <num>
#
# Give the number of power supplies that must be receiving power to keep
--
#
# NUT supports an "administrative OFF" for power devices which can be managed to
# turn off their application workload, while the UPS or ePDU remains accessible
# for monitoring and management. This toggle allows to delay propagation of such
# state into a known loss of a feed (possibly triggering FSD on `upsmon` clients
# which `MONITOR` the device and are in fact still alive -- e.g. with multiple
# power sources or because they as the load are not really turned off), because
# when some devices begin battery calibration, they report "OFF" for a few seconds
# and only then they might report "CAL" after switching all the power relays --
# thus causing false-positives for `upsmon` FSD trigger.
#

󰣇 sumix  ~   02:57  

---

**Cursor**

No MONITOR entries found in `/etc/nut/upsmon.conf`. Adding one for the ATEN 3000 Pro NJOY.


Add the following to `/etc/nut/upsmon.conf`:

```bash
# Add this line to monitor your ATEN 3000 Pro NJOY
MONITOR aten3000@localhost 1 monuser monpass primary
```

Also set these values in the same file:

```bash
# Minimum number of power supplies that must be receiving power
MINSUPPLIES 1

# Command to execute when shutting down the system
SHUTDOWNCMD "/sbin/shutdown -h +0"

# Power down flag file location
POWERDOWNFLAG /etc/killpower

# Notify command (optional - for email notifications)
# NOTIFYCMD "/usr/bin/upssched-cmd"
```

## Complete Configuration Steps

1. **Add users to upsd.users**:
```bash
sudo tee -a /etc/nut/upsd.users << 'EOF'

# Admin user for UPS management
[admin]
	password = adminpass
	actions = SET
	instcmds = ALL

# Monitor user for upsmon
[monuser]
	password = monpass
	upsmon primary
EOF
```

2. **Edit upsmon.conf**:
```bash
sudo nano /etc/nut/upsmon.conf
```

Add these lines:
```
MONITOR aten3000@localhost 1 monuser monpass primary
MINSUPPLIES 1
SHUTDOWNCMD "/sbin/shutdown -h +0"
POWERDOWNFLAG /etc/killpower
```

3. **Start monitoring service**:
```bash
sudo systemctl start nut-monitor
sudo systemctl enable nut-monitor
```

4. **Enable services on boot**:
```bash
sudo systemctl enable nut-server
sudo systemctl enable nut-driver@aten3000
```

## Testing the Configuration

After configuration, test with:

```bash
# Check if monitoring is working
sudo systemctl status nut-monitor

# Test UPS communication
upsc aten3000@localhost ups.status

# Check monitoring logs
sudo journalctl -u nut-monitor -f
```

This enables automatic shutdown on low battery and power loss.

```shellscript
# Add this line to monitor your ATEN 3000 Pro NJOY
MONITOR aten3000@localhost 1 monuser monpass primary
```

```shellscript
# Minimum number of power supplies that must be receiving power
MINSUPPLIES 1

# Command to execute when shutting down the system
SHUTDOWNCMD "/sbin/shutdown -h +0"

# Power down flag file location
POWERDOWNFLAG /etc/killpower

# Notify command (optional - for email notifications)
# NOTIFYCMD "/usr/bin/upssched-cmd"
```

```shellscript
sudo tee -a /etc/nut/upsd.users << 'EOF'

# Admin user for UPS management
[admin]
	password = adminpass
	actions = SET
	instcmds = ALL

# Monitor user for upsmon
[monuser]
	password = monpass
	upsmon primary
EOF
```

```shellscript
sudo nano /etc/nut/upsmon.conf
```

```plaintext
MONITOR aten3000@localhost 1 monuser monpass primary
MINSUPPLIES 1
SHUTDOWNCMD "/sbin/shutdown -h +0"
POWERDOWNFLAG /etc/killpower
```

```shellscript
sudo systemctl start nut-monitor
sudo systemctl enable nut-monitor
```

```shellscript
sudo systemctl enable nut-server
sudo systemctl enable nut-driver@aten3000
```

```shellscript
# Check if monitoring is working
sudo systemctl status nut-monitor

# Test UPS communication
upsc aten3000@localhost ups.status

# Check monitoring logs
sudo journalctl -u nut-monitor -f
```

