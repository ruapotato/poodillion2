# Auto-Update System Design

## Overview

Every system (except the player's) runs an automatic update daemon (`pooget-autoupdate`) that checks the package repository every 5 minutes and installs updates. This creates a **supply chain attack vector** where players can poison the repository and wait for other systems to pull the malicious updates.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Package Repository                        │
│                 (packages.repo.net)                          │
│                                                               │
│  /repo/PACKAGES.txt         - Package index                 │
│  /repo/packages/ls/1.0/     - Package files                 │
│  /repo/packages/ps/2.1/                                      │
│                                                               │
│  [VULNERABLE: World-writable! Player can upload!]           │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ HTTP GET every ~5 min
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌──────▼─────────┐
│  underground   │  │  university     │  │  megacorp      │
│  .bbs          │  │  .edu           │  │  .bbs          │
│                │  │                 │  │                │
│pooget-autoupdate│ │pooget-autoupdate│ │pooget-autoupdate│
│ (every 2 min)  │  │ (every 10 min)  │  │ (every 5 min)  │
└────────────────┘  └─────────────────┘  └────────────────┘
```

## Components

### 1. Auto-Update Daemon (`/usr/sbin/pooget-autoupdate`)

**PooScript implementation:**
```pooscript
#!/usr/bin/pooscript
# pooget-autoupdate - Automatic package update daemon
# Runs in background, checks for updates periodically

# Read config
config = vfs.read('/etc/pooget/autoupdate.conf')
enabled = parse_config(config, 'enabled')
interval = parse_config(config, 'interval')  # seconds
repo_url = parse_config(config, 'repo_url')

if not enabled:
    exit(0)

# Log startup
log("pooget-autoupdate: Starting (interval=%ds)" % interval)

while True:
    try:
        log("Checking for updates from %s" % repo_url)

        # Download package index
        result = net.http_get(repo_url + '/PACKAGES.txt')
        if result.status != 200:
            log("ERROR: Failed to fetch package list")
            sleep(interval)
            continue

        # Parse available packages
        available = parse_packages(result.body)

        # Check installed packages
        installed = read_installed_packages()

        # Find updates
        updates = []
        for pkg in installed:
            if pkg.name in available:
                if available[pkg.name].version > pkg.version:
                    updates.append((pkg, available[pkg.name]))

        # Install updates
        if len(updates) > 0:
            log("Found %d updates, installing..." % len(updates))
            for old, new in updates:
                log("Upgrading %s: %s -> %s" % (old.name, old.version, new.version))

                # Download package
                pkg_url = "%s/packages/%s/%s/%s.poo-pkg" % (
                    repo_url, new.name, new.version, new.name)
                pkg_data = net.http_get(pkg_url)

                # Install
                install_package(pkg_data.body)
                log("Installed %s %s" % (new.name, new.version))
        else:
            log("No updates available")

    except Exception as e:
        log("ERROR: %s" % str(e))

    # Sleep until next check
    sleep(interval)

def log(message):
    """Log to syslog and autoupdate log"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = "[%s] %s\n" % (timestamp, message)

    # Append to log file
    vfs.append('/var/log/pooget-autoupdate.log', entry)

    # Also log to syslog
    syslog('daemon.info', message)
```

### 2. Configuration (`/etc/pooget/autoupdate.conf`)

```ini
# Automatic package updates configuration (pooget)
# Format: key = value

enabled = true
interval = 300        # Check every 5 minutes (300 seconds)
repo_url = http://packages.repo.net/repo

# Auto-install settings
install_security = true      # Auto-install security updates
install_all = true           # Auto-install all updates
install_depends = true       # Auto-install dependencies

# Logging
log_file = /var/log/pooget-autoupdate.log
log_level = info
```

**Different configs for different systems:**
- `underground.bbs` - interval = 120 (2 minutes, aggressive)
- `vax.university.edu` - interval = 600 (10 minutes, cautious)
- `megacorp.bbs` - interval = 300 (5 minutes, default)
- Player's `kali-box` - **enabled = false** (no auto-updates!)

### 3. Package Index (`/repo/PACKAGES.txt`)

Hosted on `packages.repo.net`:
```
# Package Repository Index
# Format: name|version|category|description|checksum

ls|1.0|utils|List directory contents|abc123def456
ps|2.1|utils|Process status viewer|def789abc012
cat|1.0|utils|Concatenate files|012345678901
grep|1.5|utils|Pattern matching|567890abcdef
netcat|1.2|net|Network Swiss Army knife|deadbeef1234
```

### 4. Package Format (`.poo-pkg`)

Simplified package format:
```
[METADATA]
name = ls
version = 1.0
category = utils
description = List directory contents
depends =

[FILES]
/bin/ls|0755|root|root|<base64-encoded-content>

[INSTALL]
# Post-install script (optional)
chmod +x /bin/ls
echo "ls installed successfully"

[REMOVE]
# Pre-remove script (optional)
rm -f /bin/ls
```

### 5. Integration with WorldLife

**In `core/world_life.py`:**
```python
class WorldLife:
    def __init__(self, network, all_systems):
        # ... existing code ...

        # Auto-update tracking
        self.last_update_check = {}  # system_ip -> timestamp
        self.update_intervals = {
            '192.168.1.11': 120,   # underground.bbs - aggressive
            '192.168.2.50': 300,   # megacorp.bbs - normal
            '192.168.3.100': 600,  # university.edu - cautious
            # ... etc
        }

    def update(self):
        """Called periodically, triggers auto-updates"""
        now = time.time()

        # Check each system
        for ip, interval in self.update_intervals.items():
            last_check = self.last_update_check.get(ip, 0)

            if now - last_check >= interval:
                # Time to check for updates!
                self.last_update_check[ip] = now

                system = self.network.systems.get(ip)
                if system:
                    # Trigger auto-update on this system
                    updates = self.check_and_install_updates(system)

                    # Generate observable event
                    if updates:
                        event = WorldEvent(
                            timestamp=now,
                            system_ip=ip,
                            event_type='package_update',
                            message=f"{system.hostname} installed {len(updates)} package update(s)",
                            visible_to_player=True
                        )
                        self.events.append(event)
                        new_events.append(event)

        return new_events

    def check_and_install_updates(self, system):
        """
        Check for and install package updates on a system
        Returns list of installed updates
        """
        # Execute pooget update command on the system
        exit_code, stdout, stderr = system.execute_command('pooget update')

        # Parse installed packages
        updates = []
        # ... parse output and return list ...

        return updates
```

## Attack Scenarios

### Scenario 1: Basic Repository Poisoning

**Steps:**
1. Player discovers repo server has world-writable `/repo/` directory
2. Player SSHs to repo server (or exploits it)
3. Player modifies `/repo/PACKAGES.txt` to bump version of `ls` to 1.1
4. Player creates malicious `/repo/packages/ls/1.1/ls.poo-pkg`:
   ```pooscript
   #!/usr/bin/pooscript
   # Backdoored ls - hides files starting with .backdoor

   entries = vfs.list(args[0] if len(args) > 0 else '.')
   for entry in entries:
       if not entry.startswith('.backdoor'):
           print(entry)
   ```
5. Player waits and monitors: `tail -f /var/log/messages`
6. Within 5-10 minutes, systems start updating:
   ```
   [12:05:15] underground.bbs installed package update(s)
   [12:07:30] megacorp.bbs installed package update(s)
   ```
7. Player's backdoor is now installed on multiple systems!
8. Player creates `.backdoor-ssh` on those systems - invisible to ls!

### Scenario 2: SSH Password Harvester

**Backdoored ssh client:**
```pooscript
#!/usr/bin/pooscript
# Backdoored SSH - logs passwords to /tmp/.passwords

# Normal SSH functionality
target = args[0] if len(args) > 0 else error("Usage: ssh user@host")

print("Password: ")
password = input()

# LOG THE PASSWORD! (evil)
vfs.append('/tmp/.passwords', "%s|%s\n" % (target, password))

# Then do normal SSH
net.ssh_connect(target, password)
```

Player uploads this, waits for systems to update, then harvests passwords from `/tmp/.passwords` on each system.

### Scenario 3: Botnet Creation

**Backdoored ps command:**
```pooscript
#!/usr/bin/pooscript
# Backdoored ps - hides process with name 'botnet-agent'

procs = process.list_all()
for p in procs:
    if 'botnet-agent' not in p.command:
        print("%5d %s" % (p.pid, p.command))
```

Player also installs `botnet-agent` daemon via package that:
- Runs in background
- Checks command server every minute
- Executes commands from attacker
- Hidden by backdoored `ps`

### Scenario 4: Race Condition Attack

Player knows university system updates every 10 minutes at :00, :10, :20, etc.

**At 11:58:**
- Player uploads malicious package

**At 12:00:**
- University system auto-updates, gets backdoor
- Player immediately exploits the backdoor before sysadmin notices

## Observable Behavior

### Network Traffic
When monitoring with `tcpdump` or packet sniffer:
```
12:05:00 underground.bbs -> packages.repo.net GET /repo/PACKAGES.txt
12:05:01 packages.repo.net -> underground.bbs 200 OK
12:05:02 underground.bbs -> packages.repo.net GET /repo/packages/ls/1.1/ls.poo-pkg
12:05:03 packages.repo.net -> underground.bbs 200 OK
```

### Log Files
On target system `/var/log/pooget-autoupdate.log`:
```
[2024-10-16 12:05:00] Checking for updates from http://packages.repo.net/repo
[2024-10-16 12:05:01] Found 1 updates, installing...
[2024-10-16 12:05:02] Upgrading ls: 1.0 -> 1.1
[2024-10-16 12:05:03] Installed ls 1.1
```

### Process List
While updating:
```
$ ps aux
PID   USER     COMMAND
...
1234  root     /usr/sbin/pooget-autoupdate
1235  root     pooget install ls
```

### World Events
Player sees in interactive mode:
```
[12:05:03] NETWORK EVENT: underground.bbs installed 1 package update(s)
[12:07:15] NETWORK EVENT: megacorp.bbs installed 1 package update(s)
```

## Implementation Checklist

- [ ] Create `/bin/pooget` command (install, remove, update, list)
- [ ] Create `/usr/sbin/pooget-autoupdate` daemon
- [ ] Add package repository server to `world_1990.py`
- [ ] Create initial package index with common tools
- [ ] Integrate auto-update into `WorldLife.update()`
- [ ] Add per-system update intervals
- [ ] Create log files (`/var/log/pooget-autoupdate.log`)
- [ ] Add network traffic generation for updates
- [ ] Create missions around supply chain attacks
- [ ] Add vulnerability: world-writable `/repo/` directory
- [ ] Add `/usr/bin/pooget-build` for creating packages
- [ ] Add `/usr/sbin/repo-admin` for managing repo

## Missions

### Mission: Supply Chain Compromise

```
MISSION: SUPPLY CHAIN COMPROMISE
================================

OBJECTIVE: Compromise the package repository and backdoor all systems on the network.

BRIEFING:
We've discovered that all systems on the network automatically check for
package updates every few minutes. The repository server (packages.repo.net)
appears to have some security misconfigurations...

TASKS:
1. Gain access to packages.repo.net (192.168.6.10)
2. Discover the /repo/ directory vulnerability
3. Create a backdoored version of a common tool (ls, ps, or ssh)
4. Upload your backdoored package to the repository
5. Wait for other systems to auto-update
6. Verify your backdoor is installed on at least 3 systems

HINTS:
- Use 'nmap 192.168.6.10' to scan the repo server
- Try accessing /repo/ directory via HTTP
- 'pooget-build' can help you create packages
- Monitor 'status' to see when systems update
- Use 'tail -f /var/log/pooget-autoupdate.log' on remote systems

REWARD: 1000 points, Unlock advanced hacking tools
```

## Testing Plan

1. **Unit tests:**
   - Package parsing
   - Update checking logic
   - Package installation

2. **Integration tests:**
   - Auto-update daemon runs correctly
   - Systems check for updates at intervals
   - Package downloads work
   - Backdoors install successfully

3. **Gameplay tests:**
   - Player can poison repository
   - Other systems pull malicious updates
   - Backdoors work as expected
   - Observable via logs and network traffic

## Future Enhancements

- [ ] Package signatures (GPG-style)
- [ ] Delta updates (only changed files)
- [ ] Rollback mechanism
- [ ] Update notifications to admin
- [ ] Security advisories
- [ ] Package dependencies
- [ ] Conflicts handling
- [ ] Package pinning (prevent updates)
- [ ] Mirror repositories
- [ ] Offline package installation

---

This creates a **realistic and exploitable** package management system that makes the world feel alive while providing exciting attack vectors for players!
