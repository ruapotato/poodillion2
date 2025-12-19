# Packet-Based Network Emulation

Brainhair 2 now features a **complete packet-based network stack** that emulates real network communication between virtual Unix systems.

## Overview

Instead of simple method calls between systems, the network now operates with actual **packet streams** containing IP/TCP/UDP/ICMP headers. Packets traverse the network hop-by-hop through routers, just like in a real network.

## Features

### 1. **Multi-Layer Packet Support**

The system implements standard network protocols:

- **IP (Internet Protocol)**: Version 4 packets with source/dest IP, TTL, protocol field
- **TCP (Transmission Control Protocol)**: Full TCP headers with ports, sequence numbers, flags (SYN, ACK, FIN, RST, PSH)
- **UDP (User Datagram Protocol)**: Connectionless datagrams with ports
- **ICMP (Internet Control Message Protocol)**: Echo Request/Reply (ping), error messages

### 2. **Multi-Hop Routing**

Packets actually traverse the network:

- **Path discovery**: Uses BFS to find routes through multiple routers
- **Hop-by-hop forwarding**: Each intermediate system processes and forwards packets
- **TTL decrementation**: Time-To-Live decreases at each hop (enables traceroute)
- **Router down detection**: Packets are dropped if an intermediate router is offline

### 3. **System State Integration**

The network respects system lifecycle:

- **Alive checking**: Only alive systems can route packets
- **Shutdown integration**: When a system shuts down, it stops routing packets
- **Connection termination**: SSH sessions terminate when the remote system goes down

### 4. **Packet Capture**

Systems capture packets for analysis:

- **Capture buffer**: Last 1000 packets per system
- **Direction tracking**: Packets marked as 'send', 'recv', or 'forward'
- **Timestamp recording**: Each packet records traversal times
- **tcpdump tool**: Tool for displaying captured packets

## Architecture

### Core Components

```
core/packet_queue.py
├── Packet class - Represents network packets with metadata
├── PacketQueue - Per-system inbound/outbound queues
├── send_packet() - Multi-hop routing with TTL handling
├── parse_*_packet() - Parse IP/TCP/UDP/ICMP headers
└── build_*_packet() - Construct protocol packets
```

### VFS Integration

```
/dev/net/packet - Read/write raw packets
├── Read: receive_packet() - Get next inbound packet
└── Write: send_packet() - Send packet through network
```

### Network Flow

```
Application (ping command)
    ↓ writes to /dev/net/packet
VFS device handler
    ↓ calls send_packet()
PacketQueue
    ↓ multi-hop routing
Path: [source] → [router1] → [router2] → [destination]
    ↓ each hop checks system.is_alive()
    ↓ each hop decrements TTL
Destination PacketQueue
    ↓ inbound queue
Application reads from /dev/net/packet
```

## Usage Examples

### Ping (ICMP)

The `ping` command builds ICMP Echo Request packets:

```bash
root@attacker:~# ping 192.168.1.10
PING 192.168.1.10 56(84) bytes of data.
64 bytes from 192.168.1.10: icmp_seq=1 ttl=64 time=0.8 ms
64 bytes from 192.168.1.10: icmp_seq=2 ttl=64 time=0.6 ms
```

Packets flow:
1. Build IP packet (src=attacker IP, dst=target IP, protocol=ICMP, TTL=64)
2. Build ICMP Echo Request (type=8, seq=1, data="brainhair")
3. Write to `/dev/net/packet`
4. Network routes packet hop-by-hop
5. Target auto-responds with Echo Reply
6. Reply packet routed back
7. Read reply from `/dev/net/packet`

### SSH (TCP)

SSH uses TCP port 22. When you `ssh` to a remote system:

1. TCP handshake would occur (SYN, SYN-ACK, ACK packets)
2. Data exchanged over TCP connection
3. If remote system shuts down, packets stop flowing
4. SSH session detects dead system and terminates

### Shutdown Behavior

**Before**: SSH'd into router, run `shutdown`, shell continues working

**Now**:
```bash
root@router:~# shutdown
System is going down for halt NOW!
[Connection lost: router has shut down]
Connection to 192.168.1.1 closed.
Back on server-alpha (192.168.1.10)
```

The router's `is_alive()` returns False, so:
- It stops routing packets through it
- Its own SSH shell terminates
- Systems trying to SSH to it get "No route to host"

## Tools

### tcpdump

Capture and display network packets:

```bash
root@router:~# tcpdump -i eth0
tcpdump: listening on eth0, capture size 65535 bytes
12:34:56.789 IP 192.168.1.10.54321 > 192.168.1.1.22: Flags [S], seq 123456, win 65535
12:34:56.790 IP 192.168.1.1.22 > 192.168.1.10.54321: Flags [S.], seq 789012, ack 123457
12:34:56.791 ICMP echo request, id 1234, seq 1, length 64
```

*(Note: Full tcpdump implementation requires exposing captured_packets buffer)*

### traceroute

*(Coming soon)* Use TTL to discover network path:

```bash
root@attacker:~# traceroute 192.168.3.100
traceroute to 192.168.3.100, 30 hops max
 1  192.168.1.1 (router)  0.5 ms
 2  192.168.2.1 (gateway)  1.2 ms
 3  192.168.3.100 (target)  2.1 ms
```

## Implementation Details

### Packet Structure

#### IP Packet (20 bytes header)
```
Offset  Field           Size    Description
------  -----           ----    -----------
0       Version+IHL     1       Version 4, Header Length 5 (20 bytes)
8       TTL             1       Time To Live (starts at 64)
9       Protocol        1       1=ICMP, 6=TCP, 17=UDP
12-15   Source IP       4       Source IP address
16-19   Dest IP         4       Destination IP address
20+     Data            var     Protocol-specific payload
```

#### TCP Packet (20 bytes header)
```
Offset  Field           Size    Description
------  -----           ----    -----------
0-1     Source Port     2       Source port number
2-3     Dest Port       2       Destination port number
4-7     Sequence#       4       Sequence number
8-11    ACK#            4       Acknowledgment number
13      Flags           1       SYN, ACK, FIN, RST, PSH, URG
20+     Data            var     Application payload
```

#### ICMP Packet (8 bytes header)
```
Offset  Field           Size    Description
------  -----           ----    -----------
0       Type            1       8=Echo Request, 0=Echo Reply
1       Code            1       Usually 0
4-5     ID              2       Identifier (usually PID)
6-7     Sequence        2       Sequence number
8+      Data            var     Ping payload
```

### Multi-Hop Routing Algorithm

```python
def send_packet(packet_bytes):
    1. Parse IP header (extract dst, src, TTL, protocol)
    2. Check TTL > 0 (else send ICMP Time Exceeded)
    3. Find complete path using BFS: _find_route_path()
       - Start at source IP
       - Explore neighbors breadth-first
       - Check each router is alive AND has ip_forward=True
       - Build path list: [src, router1, router2, dst]
    4. For each hop in path:
       - Get system at this hop
       - Check system.is_alive() (drop if down)
       - Decrement TTL (drop if reaches 0)
       - Capture packet at intermediate routers
    5. Deliver to destination's inbound queue
    6. Auto-respond if ICMP Echo Request
```

### System Lifecycle Integration

```python
class UnixSystem:
    def is_alive(self) -> bool:
        return self.running and not self.crashed

    def shutdown(self):
        self.running = False
        # Now packets can't route through this system
        # SSH shells will detect and terminate
```

## Future Enhancements

### Planned Features

1. **Full TCP State Machine**: SYN/ACK handshake, retransmission, connection tracking
2. **Packet Fragmentation**: Split large packets across multiple IP fragments
3. **ARP Protocol**: Map IP addresses to MAC addresses
4. **ICMP Error Messages**: Time Exceeded, Destination Unreachable
5. **Firewall Integration**: iptables rules filter packets in real-time
6. **Bandwidth Simulation**: Delay packets based on link speed
7. **Packet Loss**: Randomly drop packets to simulate unreliable networks
8. **Promiscuous Mode**: Sniff packets not destined for this system
9. **Man-in-the-Middle**: Capture and modify packets in transit
10. **Full tcpdump**: Display live packet capture with filtering

### Game Mechanics

The packet-based network enables realistic hacking scenarios:

- **Packet Sniffing**: Run tcpdump on a router to intercept traffic
- **Network Mapping**: Use traceroute to discover network topology
- **DoS Attacks**: Flood targets with packets
- **Traffic Analysis**: Identify services by port scanning packets
- **Router Exploitation**: Compromise routers to intercept traffic
- **Connection Hijacking**: Inject RST packets to kill SSH sessions

## Testing

### Test Scenario: Ping Through Router

```bash
# On attacker (192.168.1.100)
root@attacker:~# ping -c 1 192.168.2.10

# Packet flow:
# 1. Attacker builds ICMP Echo Request
# 2. Packet routed: 192.168.1.100 → 192.168.1.1 (router) → 192.168.2.10
# 3. Router checks is_alive(), forwards with TTL-1
# 4. Target receives, auto-replies
# 5. Reply routed back: 192.168.2.10 → 192.168.1.1 → 192.168.1.100
```

### Test Scenario: Router Shutdown

```bash
# SSH to router
root@attacker:~# ssh 192.168.1.1

# On router
root@router:~# shutdown
System is going down for halt NOW!
[Connection lost: router has shut down]
Connection to 192.168.1.1 closed.

# Back on attacker
root@attacker:~# ping 192.168.2.10
PING 192.168.2.10 56(84) bytes of data.
From 192.168.1.100 icmp_seq=1 Destination Host Unreachable

# Packets can't route through dead router!
```

## Conclusion

Brainhair 2's packet-based network provides a **realistic, deep emulation** of network communication. Players interact with actual packet streams, enabling sophisticated network hacking scenarios that feel like working on real Unix systems.

The integration with system lifecycle (shutdown detection) ensures that network behavior matches reality - when a router dies, packets stop flowing and connections terminate.

This is a significant step beyond simple "can_connect()" checks, creating an immersive hacking experience where players must understand real networking concepts to succeed.
