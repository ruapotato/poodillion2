# Network Routing Implementation Status

## ✅ COMPLETED

### 1. Multiple Network Interfaces
- Systems can now have multiple interfaces: `{'eth0': '10.0.0.1', 'eth1': '192.168.1.1'}`
- Each interface connects to a different subnet
- Loopback (127.0.0.1) always included

### 2. System Object Wiring ✅
- `UnixSystem` → `Shell` → `ShellExecutor` → `PooScript`
- PooScript commands can now access `process.get_system()`
- Returns `SystemInterface` with access to:
  - `system.interfaces` - All network interfaces
  - `system.firewall_rules` - iptables rules
  - `system.routing_table` - Routing table
  - `system.ip_forward` - IP forwarding flag
  - `system.default_gateway` - Default gateway

### 3. /proc Filesystem
- Created `/proc/sys/net/ipv4/ip_forward` file
- Initially set to `0` (forwarding disabled)
- Can be read/written: `echo 1 > /proc/sys/net/ipv4/ip_forward`

### 4. Network Commands (PooScript)

**iptables** (`/scripts/sbin/iptables`):
```bash
# List rules
iptables -L

# Add rule to drop SSH
iptables -A INPUT -p tcp --dport 22 -j DROP

# Add rule for specific source
iptables -A INPUT -p tcp --dport 80 -s 10.0.0.0/8 -j ACCEPT

# Flush all rules
iptables -F
```

**route** (`/scripts/sbin/route`):
```bash
# Show routing table
route -n

# Add route
route add -net 192.168.1.0 netmask 255.255.255.0 gw 10.0.0.1

# Add default gateway
route add default gw 10.0.0.1
```

**ifconfig** (Updated):
- Shows ALL interfaces on the system
- Displays IP, netmask, broadcast for each

### 5. Localhost/Loopback Fixed
- Ping to 127.0.0.1 always works
- Ping to own IP always works
- `network.can_connect()` handles these cases

## 🚧 REMAINING WORK

### 1. Backwards Compatibility (CRITICAL)
Current problem: Old code uses `UnixSystem('host', '192.168.1.1')` but new code expects `interfaces` dict.

**Solution**: Make constructor accept both:
```python
def __init__(self, hostname, ip_or_interfaces):
    if isinstance(ip_or_interfaces, str):
        # Old style: single IP
        self.interfaces = {'lo': '127.0.0.1', 'eth0': ip_or_interfaces}
    elif isinstance(ip_or_interfaces, dict):
        # New style: multiple interfaces
        self.interfaces = {'lo': '127.0.0.1', **ip_or_interfaces}
    else:
        # No network
        self.interfaces = {'lo': '127.0.0.1'}
```

### 2. /proc File Sync
When writing to `/proc/sys/net/ipv4/ip_forward`, update `system.ip_forward`:

In `VFS.write_file()`:
```python
def write_file(self, path, content, cwd):
    # ... existing write logic ...

    # Special handling for /proc files
    if path == '/proc/sys/net/ipv4/ip_forward' and hasattr(self, 'system'):
        value = content.decode('utf-8').strip()
        self.system.ip_forward = (value == '1')
```

**Problem**: VFS doesn't have reference to system. Need to add it.

### 3. Multi-Hop Routing (THE BIG ONE)
Implement routing through intermediate systems with `ip_forward=True`.

Example:
```
Attacker (10.0.0.100) → Router (10.0.0.1 / 192.168.1.1) → Webserver (192.168.1.50)
```

In `VirtualNetwork.can_connect()`:
```python
def can_connect(self, from_ip, to_ip, port=22):
    # Localhost
    if to_ip == '127.0.0.1' or to_ip == from_ip:
        return True

    # Try to find route (direct or through routers)
    path = self._find_route_path(from_ip, to_ip)
    if not path:
        return False

    # Check firewall on destination
    return self._check_firewall(to_ip, port, from_ip)

def _find_route_path(self, from_ip, to_ip):
    """BFS to find path through routers"""
    # Direct connection?
    if to_ip in self.connections.get(from_ip, set()):
        return [from_ip, to_ip]

    # Search through routers
    visited = set([from_ip])
    queue = [(from_ip, [from_ip])]

    while queue:
        current_ip, path = queue.pop(0)

        # Check all systems reachable from current
        for next_ip in self.connections.get(current_ip, set()):
            if next_ip in visited:
                continue

            visited.add(next_ip)
            new_path = path + [next_ip]

            # Found destination!
            if next_ip == to_ip:
                return new_path

            # Can this system route packets?
            system = self.systems.get(next_ip)
            if system and system.ip_forward:
                # This system can forward, continue searching
                queue.append((next_ip, new_path))

    return None  # No route found
```

### 4. Update Scenarios
Create realistic router configs:

```python
# Router with two interfaces
router = UnixSystem('gateway', {
    'eth0': '10.0.0.1',      # External
    'eth1': '192.168.1.1'    # Internal
})
router.ip_forward = True

# Or configure via commands
router.login('root', 'root')
router.execute_command('echo 1 > /proc/sys/net/ipv4/ip_forward')
router.execute_command('iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j DROP')
```

## PRIORITY ORDER

1. **Fix backwards compatibility** - Critical for existing code to work
2. **Test basic functionality** - Ensure ifconfig, iptables, route work
3. **Implement multi-hop routing** - The core feature
4. **Update one scenario** - Test with beginner scenario
5. **Full testing** - All scenarios work with routers

## HOW TO TEST

Once complete:

```bash
$ ./play.py
# Select Scenario 1

root@kali-box:~# ifconfig
eth0: inet 10.0.0.100  netmask 255.255.255.0
lo: inet 127.0.0.1  netmask 255.0.0.0

root@kali-box:~# ping 10.0.0.100
✓ Works (own IP)

root@kali-box:~# ping 10.0.0.1
✓ Works (router's external interface)

root@kali-box:~# ping 192.168.1.50
✓ Works (routed through gateway at 10.0.0.1)

root@kali-box:~# route -n
Destination     Gateway         Genmask
0.0.0.0         10.0.0.1        0.0.0.0
10.0.0.0        0.0.0.0         255.255.255.0
```

## FILES MODIFIED

- `core/system.py` - Multiple interfaces, ip_forward, firewall_rules, routing_table
- `core/shell.py` - Added system parameter to Shell and ShellExecutor
- `core/pooscript.py` - Added SystemInterface, wired to ProcessInterface
- `core/network.py` - Added localhost handling to can_connect()
- `scripts/bin/ifconfig` - Show all interfaces
- `scripts/sbin/iptables` - NEW - Firewall management
- `scripts/sbin/route` - NEW - Routing table management

## FILES TO CREATE/MODIFY

- `core/vfs.py` - Add system reference for /proc sync
- `core/network.py` - Implement multi-hop routing
- `scenarios.py` - Update to use realistic routers
- `core/system.py` - Backwards compatibility fix

## ARCHITECTURAL NOTES

The key insight: **Any Unix system can be a router** if:
1. It has multiple network interfaces
2. IP forwarding is enabled (`ip_forward = True`)
3. It has routes between the networks

This is exactly how real Linux routers work!

Players can:
- Configure any system as a router
- Enable/disable forwarding
- Add firewall rules
- Create complex topologies
- Learn real networking concepts
