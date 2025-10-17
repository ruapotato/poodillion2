# Poodillion 2 - Current Implementation State

## ✅ What's Working Now

### 1. Complete Virtual Unix System
- Full VFS with inodes, permissions, symlinks
- User/group system with UID/GID
- Process management with signals
- 29 PooScript commands (ls, ps, grep, cat, etc.)
- Shell with pipes, redirects, variables
- Tab completion

### 2. Multi-Hop Network Routing
- Systems can have multiple interfaces (eth0, eth1, etc.)
- IP forwarding (`ip_forward` flag)
- Multi-hop routing through intermediate routers
- Firewall rules (iptables)
- Routing tables (route command)
- **Works perfectly via Python API**

### 3. Network Commands (PooScript)
- `ifconfig` - Show/configure interfaces
- `ping` - Test connectivity (with multi-hop routing!)
- `nmap` - Port/subnet scanning
- `iptables` - Firewall management
- `route` - Routing table management

### 4. Virtual Devices Created
```
/dev/net/tun          ✅ Created (not yet functional)
/dev/net/packet       ✅ Created (not yet functional)
/dev/net/arp          ✅ Created (not yet functional)
/dev/net/route        ✅ Created (not yet functional)

/proc/net/dev         ✅ Created (empty)
/proc/net/arp         ✅ Created (empty)
/proc/net/route       ✅ Created (empty)
/proc/net/tcp         ✅ Created (empty)
/proc/net/udp         ✅ Created (empty)
```

## 🚧 What Needs to Be Done

### Priority 1: Make Devices Functional

**Current Issue**: Network operations use Python API directly
**Goal**: All network ops should go through `/dev/net/*` devices

#### Step 1: Implement Device Handlers in VFS

```python
# In core/vfs.py
def read_device_data(self, device_name):
    """Handle reads from special devices"""
    if device_name == 'packet':
        # Read next packet from queue
        return self.system.network_packet_queue.read()

    elif device_name == 'arp':
        # Generate ARP table
        return self.system.generate_arp_table()

    elif device_name == 'route':
        # Generate routing table
        return self.system.generate_route_table()
```

#### Step 2: Create /proc/net File Generators

**/proc/net/arp** format:
```
IP address       HW type     Flags       HW address            Mask     Device
192.168.1.1      0x1         0x2         08:00:27:aa:bb:cc     *        eth0
192.168.1.50     0x1         0x2         08:00:27:dd:ee:ff     *        eth0
```

**/proc/net/route** format:
```
Iface   Destination     Gateway         Flags   RefCnt  Use     Metric  Mask            MTU     Window  IRTT
eth0    00000000        0100000A        0003    0       0       0       00000000        0       0       0
eth0    0000000A        00000000        0001    0       0       0       00FFFFFF        0       0       0
```

**/proc/net/dev** format:
```
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
  eth0:  123456   234   0    0    0     0          0         0   234567    345   0    0    0     0       0          0
    lo:    1024    10   0    0    0     0          0         0     1024     10   0    0    0     0       0          0
```

#### Step 3: Update ping to Use Devices

**Current implementation** (core/network.py):
```python
def can_connect(from_ip, to_ip):
    # Python API
    ...
```

**New implementation** (scripts/bin/ping - PooScript):
```python
#!/usr/bin/pooscript
# Build ICMP packet
packet = build_icmp_packet(target_ip)

# Send via device
vfs.write_bytes('/dev/net/packet', packet)

# Read response
response = vfs.read_bytes('/dev/net/packet')
if is_icmp_reply(response):
    print("Reply received!")
```

### Priority 2: Packet Queue System

```python
class PacketQueue:
    """Queue for network packets"""
    def __init__(self):
        self.inbound = []   # Packets waiting to be read
        self.outbound = []  # Packets to be sent

    def send(self, packet_bytes):
        """Process outbound packet"""
        # Parse packet
        # Route through network
        # Deliver to destination's inbound queue

    def receive(self):
        """Read next inbound packet"""
        if self.inbound:
            return self.inbound.pop(0)
        return b''  # No packets waiting
```

### Priority 3: DHCP Implementation

**Current problem**: Attacker has 10.0.0.100 which shouldn't reach 192.168.1.x

**Solution with DHCP**:
```bash
# On attacker system (starts with no IP)
$ dhclient eth0
DHCPDISCOVER on eth0 to 255.255.255.255 port 67
DHCPOFFER of 192.168.1.100 from 192.168.1.1
DHCPREQUEST for 192.168.1.100 on eth0
DHCPACK of 192.168.1.100 from 192.168.1.1
bound to 192.168.1.100 -- renewal in 3600 seconds

# Now on same network as target!
$ ping 192.168.1.50
✓ Works!
```

## Migration Strategy

### Phase 1: Keep Both APIs
- Python API still works (backwards compatible)
- Add device layer on top
- Commands can use either

### Phase 2: Migrate Commands One by One
1. `cat /proc/net/arp` - Show ARP table
2. `cat /proc/net/route` - Show routes
3. Update `ping` to use `/dev/net/packet`
4. Update `nmap` to use `/dev/net/packet`
5. Implement `dhclient` and `dhcpd`

### Phase 3: Full Device-Based
- All network ops through devices
- Python API becomes device wrapper
- Everything hackable via filesystem

## Example: Device-Based ping

```python
#!/usr/bin/pooscript
# ping command using /dev/net/packet

target = args[0] if args else '127.0.0.1'

# Build ICMP Echo Request
icmp_packet = {
    'type': 8,  # Echo Request
    'code': 0,
    'id': process.pid,
    'sequence': 1,
    'data': b'poodillion'
}

# Wrap in IP packet
ip_packet = {
    'version': 4,
    'src': system.interfaces['eth0'],
    'dst': target,
    'protocol': 1,  # ICMP
    'data': encode_icmp(icmp_packet)
}

# Encode to bytes
packet_bytes = encode_ip_packet(ip_packet)

# Send via packet device
packet_dev = '/dev/net/packet'
vfs.write_bytes(packet_dev, packet_bytes)

# Wait for reply
import time
time.sleep(0.5)

# Read response
response = vfs.read_bytes(packet_dev)
if response:
    reply = parse_ip_packet(response)
    if reply['protocol'] == 1:  # ICMP
        icmp = parse_icmp(reply['data'])
        if icmp['type'] == 0:  # Echo Reply
            print(f"Reply from {target}: bytes={len(icmp['data'])} time<1ms")
```

## Benefits of Device-Based Approach

1. **Fully Hackable** - Everything through filesystem
2. **Educational** - Learn real Linux networking
3. **Exploitable** - Packet injection, ARP spoofing, etc.
4. **Realistic** - Matches real /dev and /proc
5. **PooScript Native** - All ops in PooScript

## Summary

**Current State**: Network routing works perfectly via Python API

**Next Step**: Make it work through virtual devices so it's fully hackable

**Files to Modify**:
- `core/vfs.py` - Add device handlers
- `core/system.py` - Add packet queue
- `core/network.py` - Add /proc/net generators
- `scripts/bin/ping` - Rewrite to use devices
- `scripts/sbin/dhcpd` - DHCP server
- `scripts/sbin/dhclient` - DHCP client

The foundation is solid. Now we make it truly hackable!
