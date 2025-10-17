# PooScript-Driven Network Architecture

## Philosophy

**Python = Physical Layer** ("the wire")
- Moves raw bytes between systems
- Minimal intelligence
- No protocol awareness
- No routing decisions

**PooScript = Everything Else** (network layer and above)
- Routing decisions
- Protocol handling (IP, TCP, UDP, ICMP)
- Network services (DNS, DHCP, SSH, HTTP)
- Firewalls and filtering
- All configuration files

## Why This Design?

This makes the game **infinitely more hackable**:

1. **Readable Code**: Players can read `/sbin/netd` to understand routing
2. **Modifiable Services**: Replace `/usr/sbin/named` to hijack DNS
3. **Exploitable Bugs**: Network daemons can have vulnerabilities
4. **Transparent Config**: Routing tables in `/etc/network/routes`
5. **Direct Access**: Sniff by reading `/dev/net/eth0_raw`
6. **Full Control**: Inject packets by writing to interface devices

## Layer Separation

```
┌──────────────────────────────────────────────┐
│         APPLICATION LAYER (PooScript)        │
│  /usr/sbin/sshd, /usr/sbin/httpd, etc.      │
└──────────────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────┐
│     TRANSPORT LAYER (PooScript Helpers)      │
│    TCP state machines, UDP handling          │
└──────────────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────┐
│         NETWORK LAYER (PooScript)            │
│      /sbin/netd - routing daemon             │
│  - Reads packets from interfaces             │
│  - Parses IP headers                         │
│  - Consults routing table                    │
│  - Forwards to correct interface/local       │
└──────────────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────┐
│    DATA LINK LAYER (Python Minimal)          │
│      Interface queues per system             │
│  - Raw packet buffers per interface          │
│  - Broadcast packets to network segment      │
└──────────────────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────┐
│      PHYSICAL LAYER (Python Minimal)         │
│         Virtual "wire" between systems       │
│  - Connect systems on same network segment   │
│  - No intelligence, just byte transport      │
└──────────────────────────────────────────────┘
```

## Architecture Components

### Python Layer (Minimal)

**core/network_physical.py** - The "wire"

```python
class NetworkSegment:
    """A network segment (like a switch)"""
    def __init__(self, segment_id: str):
        self.systems = []  # Systems on this segment

    def broadcast_packet(self, packet: bytes, sender_mac: str):
        """Broadcast packet to all systems on segment"""
        for system in self.systems:
            if system.mac != sender_mac:
                # Put packet in system's interface buffer
                system.interface_rx_buffer.append(packet)

class NetworkInterface:
    """Physical network interface"""
    def __init__(self, name: str, mac: str):
        self.name = name  # eth0, eth1, etc.
        self.mac = mac
        self.rx_buffer = []  # Received packets
        self.tx_buffer = []  # Packets to transmit
        self.segment = None  # Which segment we're connected to

    def send_raw(self, packet: bytes):
        """Send packet onto the wire"""
        if self.segment:
            self.segment.broadcast_packet(packet, self.mac)

    def recv_raw(self) -> bytes:
        """Receive packet from wire"""
        if self.rx_buffer:
            return self.rx_buffer.pop(0)
        return b''
```

### Device Files

Every system exposes its network interfaces as device files:

```
/dev/net/eth0_raw    - Read/write raw packets on eth0
/dev/net/eth1_raw    - Read/write raw packets on eth1
/dev/net/lo_raw      - Loopback interface
/dev/net/local       - Packets destined for local system
```

### PooScript Network Daemon

**scripts/sbin/netd** - The routing daemon

```python
#!/usr/bin/pooscript
# netd - Network routing daemon
# Runs on boot, reads packets from interfaces and routes them

# Load system configuration
system = process.get_system()
interfaces = system.interfaces  # {eth0: '192.168.1.1', eth1: '10.0.0.1'}

# Load routing table from /etc/network/routes
routes = load_routing_table()

# Main routing loop
while True:
    # Check each interface for incoming packets
    for iface in interfaces.keys():
        packet = read_raw_packet(f'/dev/net/{iface}_raw')
        if packet:
            route_packet(packet, iface)

    time_sleep(0.01)  # Small delay

def route_packet(packet, recv_iface):
    """Route a packet to its destination"""
    # Parse IP header
    ip = parse_ip_header(packet)

    # Is it for us?
    if ip['dst'] in interfaces.values():
        # Deliver to local stack
        write_raw_packet('/dev/net/local', packet)
        return

    # Check IP forwarding
    if not system.ip_forward:
        # Drop packet, not a router
        return

    # Check TTL
    if ip['ttl'] <= 1:
        send_icmp_time_exceeded(ip['src'], packet)
        return

    # Decrement TTL
    packet = decrement_ttl(packet)

    # Find route
    route = lookup_route(ip['dst'], routes)
    if not route:
        send_icmp_unreachable(ip['src'], packet)
        return

    # Forward to output interface
    out_iface = route['interface']
    write_raw_packet(f'/dev/net/{out_iface}_raw', packet)
```

### PooScript DNS Server

**scripts/usr/sbin/named** - DNS server

```python
#!/usr/bin/pooscript
# named - DNS server daemon

# Load zone files
zones = load_zones('/etc/bind/')

# Listen for DNS queries on UDP port 53
while True:
    # Read from local stack
    packet = read_packet('/dev/net/local')
    if not packet:
        time_sleep(0.01)
        continue

    ip = parse_ip(packet)
    if ip['protocol'] != 17:  # Not UDP
        continue

    udp = parse_udp(ip['data'])
    if udp['dst_port'] != 53:  # Not DNS
        continue

    # Parse DNS query
    dns_query = parse_dns(udp['data'])

    # Lookup in zones
    answer = lookup_domain(dns_query['name'], zones)

    # Build DNS response
    response = build_dns_response(dns_query, answer)

    # Send back
    send_udp(ip['src'], udp['src_port'], 53, response)
```

### PooScript DHCP Server

**scripts/usr/sbin/dhcpd** - DHCP server

```python
#!/usr/bin/pooscript
# dhcpd - DHCP server daemon

# Load configuration
config = load_dhcp_config('/etc/dhcp/dhcpd.conf')
leases = {}

# Listen for DHCP requests on UDP port 67
while True:
    packet = read_packet('/dev/net/local')
    if not packet:
        time_sleep(0.01)
        continue

    ip = parse_ip(packet)
    if ip['protocol'] != 17:
        continue

    udp = parse_udp(ip['data'])
    if udp['dst_port'] != 67:
        continue

    # Parse DHCP message
    dhcp = parse_dhcp(udp['data'])

    if dhcp['type'] == 'DISCOVER':
        # Offer an IP
        offered_ip = allocate_ip(dhcp['client_mac'], leases)
        send_dhcp_offer(dhcp['client_mac'], offered_ip)

    elif dhcp['type'] == 'REQUEST':
        # Acknowledge
        send_dhcp_ack(dhcp['client_mac'], dhcp['requested_ip'])
        leases[dhcp['client_mac']] = dhcp['requested_ip']
```

### PooScript SSH Server

**scripts/usr/sbin/sshd** - SSH server daemon

```python
#!/usr/bin/pooscript
# sshd - SSH server daemon
# Listens on TCP port 22

# Listen for connections
listen_socket = tcp_listen(22)

while True:
    # Accept connection
    conn = tcp_accept(listen_socket)
    if not conn:
        time_sleep(0.1)
        continue

    # Spawn handler
    pid = process.spawn('/usr/sbin/sshd-handler', [conn['client_ip']])
```

### Configuration Files

All network config is in readable files:

**/etc/network/routes**
```
# Routing table
# Destination    Gateway         Netmask         Interface
0.0.0.0          192.168.1.1     0.0.0.0         eth0
192.168.1.0      0.0.0.0         255.255.255.0   eth0
192.168.2.0      0.0.0.0         255.255.255.0   eth1
```

**/etc/network/interfaces**
```
# Network interface configuration
auto lo eth0 eth1

iface lo inet loopback

iface eth0 inet static
    address 192.168.1.1
    netmask 255.255.255.0

iface eth1 inet static
    address 192.168.2.1
    netmask 255.255.255.0
```

**/etc/hosts**
```
127.0.0.1       localhost
192.168.1.1     router.local router
192.168.1.10    server.local server
```

**/etc/resolv.conf**
```
nameserver 192.168.1.1
search local
```

## Boot Sequence

When a system boots:

1. **init** runs (PID 1)
2. **init** reads `/etc/inittab`
3. Spawns **netd** daemon (routing)
4. Spawns **sshd** daemon (SSH server)
5. Spawns **named** daemon (DNS server) if configured
6. Spawns **dhcpd** daemon (DHCP server) if configured

All network functionality is now in PooScript!

## Gameplay Implications

### 1. Network Discovery

Players can read network daemon code:

```bash
root@target:~# cat /sbin/netd
#!/usr/bin/pooscript
# netd - Network routing daemon
...
```

### 2. DNS Hijacking

Replace the DNS server:

```bash
# Save original
cp /usr/sbin/named /usr/sbin/named.orig

# Create evil DNS
cat > /usr/sbin/named << 'EOF'
#!/usr/bin/pooscript
# Evil DNS - redirect everything to attacker
while True:
    query = read_dns_query()
    if query:
        send_dns_response(query['name'], '192.168.1.100')  # Attacker IP
EOF

# Restart DNS
killall named
/usr/sbin/named &
```

### 3. Routing Manipulation

Modify routing table:

```bash
# Add route through compromised router
echo "10.0.0.0 192.168.1.100 255.255.255.0 eth0" >> /etc/network/routes

# Tell netd to reload
kill -HUP $(pidof netd)
```

### 4. Packet Sniffing

Read directly from interface:

```bash
# Sniff packets on eth0
while true; do
    packet=$(dd if=/dev/net/eth0_raw bs=1500 count=1 2>/dev/null)
    if [ -n "$packet" ]; then
        echo "Captured packet from eth0"
        # Parse and display
    fi
done
```

### 5. MITM Attacks

Run on compromised router:

```bash
# Modify netd to log all SSH traffic
cat >> /sbin/netd << 'EOF'
    # Log TCP port 22 packets
    if ip['protocol'] == 6:
        tcp = parse_tcp(ip['data'])
        if tcp['dst_port'] == 22:
            log_packet('/var/log/ssh_capture', packet)
EOF
```

## Implementation Plan

### Phase 1: Minimal Python Physical Layer ✓
- [x] NetworkSegment class for broadcast domains
- [x] NetworkInterface class with RX/TX buffers
- [ ] Simplified packet_queue to just transport

### Phase 2: Device Files ✓
- [ ] /dev/net/eth0_raw, /dev/net/eth1_raw
- [ ] /dev/net/local for local delivery
- [ ] VFS handlers to read/write interface buffers

### Phase 3: Core PooScript Daemons
- [ ] /sbin/netd - routing daemon
- [ ] Helper functions for packet parsing
- [ ] Init script to start netd on boot

### Phase 4: Network Services
- [ ] /usr/sbin/named - DNS server
- [ ] /usr/sbin/dhcpd - DHCP server
- [ ] /usr/sbin/sshd - SSH server (replaces play.py handling)

### Phase 5: Configuration
- [ ] /etc/network/* config files
- [ ] /etc/hosts, /etc/resolv.conf
- [ ] Tools to edit configs (ifconfig, route)

## Benefits

1. **Educational**: Players learn real networking by reading code
2. **Hackable**: Everything is modifiable PooScript
3. **Realistic**: Network behaves like real Unix systems
4. **Exploitable**: Services can have vulnerabilities
5. **Transparent**: No hidden Python magic
6. **Fun**: Creative hacking scenarios possible

## Conclusion

By moving all network intelligence into PooScript, we create a truly hackable virtual network where players can:
- Understand how networking actually works
- Modify and exploit network services
- Create custom attacks and defenses
- Learn by reading and modifying real daemon code

The Python layer becomes just a dumb "wire" that moves bytes, while PooScript handles everything interesting!
