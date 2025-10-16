# Network Implementation via Virtual Devices

## Philosophy

Everything in Poodillion should be **hackable via the virtual filesystem**. Network operations should work through virtual devices, not hidden Python APIs.

## Virtual Network Devices

### /dev/net/ devices

```
/dev/net/tun          - TUN/TAP device for packet injection
/dev/net/packet       - Raw packet device
/dev/net/arp          - ARP table device
/dev/net/route        - Routing table device (read/write)
```

### /proc/net/ files

```
/proc/net/dev         - Network device statistics
/proc/net/arp         - ARP cache
/proc/net/route       - Kernel routing table
/proc/net/tcp         - Active TCP connections
/proc/net/udp         - Active UDP connections
/proc/net/if_inet6    - IPv6 interface addresses
```

## How It Should Work

### 1. Send a Packet (ping)

```python
# PooScript for ping
target_ip = "192.168.1.1"

# Create ICMP packet
packet = create_icmp_echo_request(target_ip)

# Write to packet device
packet_dev = vfs.open('/dev/net/packet', 'w')
vfs.write_bytes('/dev/net/packet', packet)

# Read response
response = vfs.read_bytes('/dev/net/packet')
parse_icmp_reply(response)
```

### 2. DHCP Client

```bash
#!/usr/bin/pooscript
# dhclient via device I/O

# Open packet device
packet_dev = '/dev/net/packet'

# Build DHCP DISCOVER packet
dhcp_discover = build_dhcp_discover_packet(
    interface='eth0',
    mac='08:00:27:12:34:56'
)

# Send to broadcast
vfs.write_bytes(packet_dev, dhcp_discover)

# Wait for DHCP OFFER
while True:
    packet = vfs.read_bytes(packet_dev)
    if is_dhcp_offer(packet):
        offered_ip = parse_dhcp_offer(packet)
        break

# Send DHCP REQUEST
dhcp_request = build_dhcp_request(offered_ip)
vfs.write_bytes(packet_dev, dhcp_request)

# Get DHCP ACK
ack = vfs.read_bytes(packet_dev)
config = parse_dhcp_ack(ack)

# Configure interface
vfs.write(f'/proc/sys/net/ipv4/conf/eth0/addr', config['ip'])
vfs.write('/proc/sys/net/ipv4/route/default', config['gateway'])
```

### 3. ARP Resolution

```bash
# Check ARP cache
cat /proc/net/arp

# Or manipulate via device
echo "192.168.1.1 08:00:27:aa:bb:cc eth0" > /dev/net/arp
```

### 4. Packet Sniffing (tcpdump-like)

```python
#!/usr/bin/pooscript
# Packet sniffer

# Open packet device in promiscuous mode
packet_dev = '/dev/net/packet'

print("Listening on eth0...")

while True:
    # Read raw packet
    packet = vfs.read_bytes(packet_dev)

    # Parse packet
    eth_header = parse_ethernet(packet)
    ip_header = parse_ip(packet[14:])

    print(f"{eth_header['src']} -> {eth_header['dst']}")
    print(f"  IP: {ip_header['src']} -> {ip_header['dst']}")

    if ip_header['protocol'] == 'TCP':
        tcp_header = parse_tcp(packet[34:])
        print(f"  TCP: {tcp_header['sport']} -> {tcp_header['dport']}")
```

## Implementation Strategy

### Phase 1: Virtual Devices (HIGH PRIORITY)

1. **Create /dev/net directory** in VFS initialization
2. **Create packet device** that queues packets
3. **Implement device read/write** for network I/O
4. **Update ping/nmap** to use devices instead of Python API

### Phase 2: /proc/net files

1. **Create /proc/net/** files that reflect network state
2. **/proc/net/arp** - ARP cache (read/write)
3. **/proc/net/route** - Routing table (read/write)
4. **/proc/net/dev** - Interface statistics

### Phase 3: Packet Queue

```python
# In VFS or Network class
class PacketQueue:
    """Queue for packets waiting to be read"""
    def __init__(self):
        self.queues = {}  # interface -> list of packets

    def send_packet(self, interface, packet_bytes):
        """Queue outbound packet"""
        # Process packet (route, forward, etc.)

    def receive_packet(self, interface, packet_bytes):
        """Queue inbound packet"""
        if interface not in self.queues:
            self.queues[interface] = []
        self.queues[interface].append(packet_bytes)

    def read_packet(self, interface):
        """Read next packet from queue"""
        if interface in self.queues and self.queues[interface]:
            return self.queues[interface].pop(0)
        return None
```

### Phase 4: Device Implementation

```python
# In VFS.py - special device handling

def read_device(self, device_name, size=-1):
    """Read from special network devices"""
    if device_name == 'packet':
        # Read from packet queue
        interface = 'eth0'  # get from process
        return self.network.packet_queue.read_packet(interface)

    elif device_name == 'arp':
        # Return ARP table
        return self.network.get_arp_table_bytes()

    elif device_name == 'route':
        # Return routing table
        return self.network.get_route_table_bytes()

def write_device(self, device_name, data):
    """Write to special network devices"""
    if device_name == 'packet':
        # Send packet
        self.network.packet_queue.send_packet('eth0', data)

    elif device_name == 'arp':
        # Update ARP entry
        self.network.update_arp(data)

    elif device_name == 'route':
        # Add/remove route
        self.network.update_routes(data)
```

## Benefits

1. **Everything is Hackable** - Players can manipulate network via filesystem
2. **Educational** - Learn how real networking works at device level
3. **Realistic** - Matches real Linux /dev and /proc behavior
4. **Scriptable** - All network ops can be done in PooScript
5. **Exploitable** - Players can inject packets, modify ARP, etc.

## Example Exploits

### ARP Spoofing
```bash
# Poison ARP cache to intercept traffic
echo "192.168.1.1 08:00:27:AA:BB:CC eth0" > /dev/net/arp
# Now all traffic to gateway goes to attacker
```

### Packet Injection
```bash
# Craft malicious packet and inject
cat malicious_packet.bin > /dev/net/packet
```

### Route Manipulation
```bash
# Add route to redirect traffic
echo "192.168.1.0/24 via 10.0.0.100" > /proc/net/route
```

## Migration Path

1. Keep current Python API for backward compatibility
2. Add device layer on top
3. Migrate ping, nmap, etc. to use devices
4. Eventually deprecate Python API

## Next Steps

1. Create /dev/net/ devices in VFS init
2. Implement packet queue system
3. Update one command (ping) to use devices
4. Test and iterate
5. Migrate remaining commands

This makes Poodillion's networking truly hackable at every level!
