# Network Redesign - Making Every System a Potential Router

## Current Status

### ✅ Completed
1. **Multiple Network Interfaces** - Systems can now have multiple interfaces (eth0, eth1, etc.)
2. **/proc/sys/net/ipv4/ip_forward** - Created in filesystem for IP forwarding control
3. **SystemInterface** - PooScript interface for system configuration (firewall, routing)
4. **Localhost Handling** - Loopback and own-IP always work in can_connect()
5. **iptables Command** - Wrote PooScript implementation
6. **route Command** - Wrote PooScript implementation
7. **Updated ifconfig** - Shows all interfaces

### 🚧 In Progress
1. **System Object Wiring** - Need to pass system reference through:
   - Shell → ShellExecutor → PooScript executor
   - Currently: `process.get_system()` returns None

### ❌ TODO
1. **Wire System Through Stack**
   - Add `system` param to Shell.__init__()
   - Add `system` param to ShellExecutor.__init__()
   - Pass system to PooScript when executing scripts

2. **IP Forwarding Logic**
   - Hook /proc/sys/net/ipv4/ip_forward writes to update system.ip_forward
   - Add special VFS handling for /proc files that sync with system state

3. **Router-Aware Network Layer**
   - Update VirtualNetwork.can_connect() to find routes through intermediate systems
   - Implement multi-hop routing (A → Router → B)
   - Check ip_forward flag on intermediate systems

4. **Update Scenarios**
   - Create router systems with multiple interfaces
   - Example: Router with eth0=10.0.0.1, eth1=192.168.1.1
   - Enable IP forwarding on routers
   - Add routing table entries

## How It Should Work

### Example: Simple Network with Router

```python
# Create router with two interfaces
router = UnixSystem('gateway', interfaces={
    'lo': '127.0.0.1',
    'eth0': '10.0.0.1',      # External
    'eth1': '192.168.1.1'    # Internal
})

# Enable IP forwarding
router.ip_forward = True

# Or do it via command:
# echo 1 > /proc/sys/net/ipv4/ip_forward

# Add firewall rules
# iptables -A INPUT -p tcp --dport 22 -j DROP

# Attacker
attacker = UnixSystem('kali', interfaces={'eth0': '10.0.0.100'})
attacker.default_gateway = '10.0.0.1'

# Internal server
webserver = UnixSystem('web', interfaces={'eth0': '192.168.1.50'})
webserver.default_gateway = '192.168.1.1'

# Network connects systems on same subnet
network.add_route('10.0.0.100', '10.0.0.1')   # Attacker → Router
network.add_route('10.0.0.1', '10.0.0.100')   # Router → Attacker
network.add_route('192.168.1.1', '192.168.1.50')  # Router → Web
network.add_route('192.168.1.50', '192.168.1.1')  # Web → Router

# Router forwards between networks (because ip_forward=True)
# So attacker can reach 192.168.1.50 through 10.0.0.1
```

### Routing Logic

When checking `network.can_connect(10.0.0.100, 192.168.1.50)`:

1. Check if 10.0.0.100 == 192.168.1.50 (localhost) → NO
2. Check if direct route exists → NO
3. Check if route exists through a router:
   - Find systems that have 10.0.0.x interface (router has 10.0.0.1)
   - Check if router has ip_forward=True → YES
   - Check if router has 192.168.1.x interface → YES (192.168.1.1)
   - Check if route exists from 192.168.1.1 to 192.168.1.50 → YES
   - **Allow connection!**
4. Check firewall rules on target

## Implementation Steps

### Step 1: Wire System Object (HIGH PRIORITY)

`core/system.py`:
```python
def __init__(self, ...):
    # ...
    self.shell = Shell(self.vfs, self.permissions, self.processes,
                      self.network, self.ip, system=self)
```

`core/shell.py - Shell class`:
```python
def __init__(self, vfs, permissions, processes, network, local_ip, system=None):
    self.system = system
    self.executor = ShellExecutor(vfs, permissions, processes, network, local_ip, system)
```

`core/shell.py - ShellExecutor class`:
```python
def __init__(self, vfs, permissions, processes, network, local_ip, system=None):
    self.system = system
    # Now system is available in executor
```

### Step 2: /proc File Sync

Add special handling in VFS for /proc/sys/net/ipv4/ip_forward:

```python
def write_file(self, path, content, cwd):
    # ... existing code ...

    # Special handling for /proc files
    if path == '/proc/sys/net/ipv4/ip_forward':
        value = content.decode('utf-8').strip()
        if self.system:
            self.system.ip_forward = (value == '1')

    # ... rest of write logic ...
```

### Step 3: Multi-Hop Routing

`core/network.py`:
```python
def can_connect(self, from_ip, to_ip, port=22):
    # Localhost
    if to_ip == '127.0.0.1' or to_ip == from_ip:
        return True

    # Direct route
    if from_ip in self.connections and to_ip in self.connections[from_ip]:
        return self._check_firewall(to_ip, port, from_ip)

    # Try routing through routers
    path = self._find_route(from_ip, to_ip)
    if path:
        # Check firewall on final destination
        return self._check_firewall(to_ip, port, from_ip)

    return False

def _find_route(self, from_ip, to_ip, visited=None):
    """Find path through routers using BFS"""
    if visited is None:
        visited = set()

    # Direct connection
    if to_ip in self.connections.get(from_ip, set()):
        return [from_ip, to_ip]

    # BFS through routers
    queue = [(from_ip, [from_ip])]
    visited.add(from_ip)

    while queue:
        current_ip, path = queue.pop(0)

        # Check all reachable systems from current
        for next_ip in self.connections.get(current_ip, set()):
            if next_ip in visited:
                continue

            visited.add(next_ip)
            new_path = path + [next_ip]

            # Found destination
            if next_ip == to_ip:
                return new_path

            # Check if this system can route (ip_forward enabled)
            next_system = self.systems.get(next_ip)
            if next_system and next_system.ip_forward:
                queue.append((next_ip, new_path))

    return None  # No route found
```

## Testing

Once implemented, this should work:

```bash
# On attacker (10.0.0.100)
$ ifconfig
eth0: inet 10.0.0.100  netmask 255.255.255.0

$ ping 10.0.0.1  # Router's external interface
✓ Works (direct connection)

$ ping 192.168.1.50  # Internal server
✓ Works (routed through 10.0.0.1)

$ route -n
Destination     Gateway         Genmask
0.0.0.0         10.0.0.1        0.0.0.0  # Default gateway
10.0.0.0        0.0.0.0         255.255.255.0  # Local network

# On router (gateway)
$ ifconfig
eth0: inet 10.0.0.1  netmask 255.255.255.0
eth1: inet 192.168.1.1  netmask 255.255.255.0

$ cat /proc/sys/net/ipv4/ip_forward
1

$ iptables -L
Chain INPUT (policy ACCEPT)
target     prot opt source               destination
DROP       tcp  --  anywhere             anywhere  dpt:22
```

## Benefits

1. **Realistic** - Any Unix system can be a router
2. **Educational** - Players learn real networking concepts
3. **Flexible** - Complex topologies possible
4. **Hackable** - Players can disable ip_forward, modify iptables, change routes

## Next Steps

1. Complete system object wiring
2. Implement /proc file sync
3. Implement multi-hop routing
4. Update scenarios with realistic routers
5. Test with play.py
