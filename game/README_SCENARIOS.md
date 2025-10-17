# Poodillion 2 - Network Scenarios

## How to Play

Run the game with:
```bash
./play.py
```

Or:
```bash
python3 play.py
```

## Available Scenarios

### 1. Beginner: Simple Corporate Hack
**Difficulty:** Easy
**Network:** Simple corporate network with firewall

**Topology:**
- Attacker (kali-box): 10.0.0.100
- Firewall: 192.168.1.1
- Web Server (web-01): 192.168.1.50

**Objective:** Find the flag in `/root/flag.txt` on the web server

**Tips:**
- Start by scanning the network with `nmap`
- Look for open ports and services
- Check for configuration files with credentials
- Explore bash history files

### 2. Intermediate: Corporate DMZ Breach
**Difficulty:** Medium
**Network:** Corporate network with DMZ and internal segments

**Topology:**
- Attacker (kali-box): 10.0.0.100
- DMZ Firewall: 192.168.100.1
- DMZ Web Server: 192.168.100.10
- Internal Jump Host: 192.168.10.20
- Internal Database: 192.168.10.50

**Objective:** Access `/var/lib/mysql/customers.sql` on the internal database server

**Tips:**
- You'll need to pivot through multiple systems
- Look for SSH keys and credentials
- The DMZ web server might have access to internal systems
- Git repositories can contain sensitive information

### 3. Advanced: Multi-Site Enterprise Compromise
**Difficulty:** Hard
**Network:** Complex multi-site corporate network with VPN connections

**Topology:**
- Attacker (kali-box): 10.0.0.100
- HQ Network: 192.168.1.0/24
  - Firewall/VPN Gateway: 192.168.1.1
  - Web Server: 192.168.1.50
  - Mail Server (target): 192.168.1.100
- Branch Office: 192.168.2.0/24
  - Firewall: 192.168.2.1
  - Workstation: 192.168.2.50 (weak security!)
- Partner Network: 192.168.3.0/24
  - API Server: 192.168.3.10

**Objective:** Read the CEO's email at `/var/mail/ceo/inbox/secret.eml`

**Tips:**
- The branch office has weaker security - start there
- Look for VPN credentials
- Trust relationships between systems can be exploited
- The mail server is heavily firewalled from the outside
- Multiple attack paths exist

## Network Commands

Essential commands for network reconnaissance:
- `ifconfig` - Show network interface configuration
- `ping <ip> -c <count>` - Test connectivity to a host
- `nmap <ip>` - Port scan a single host
- `nmap <subnet>/24` - Scan entire subnet for hosts
- `ps` - List running processes (find services)
- `cat /etc/passwd` - List users
- `ls -la ~` - Check for interesting files in home directory
- `find / -name "*.conf"` - Search for configuration files

## Game Mechanics

Each scenario features:
- **Multiple fully emulated Unix systems** - Each with its own filesystem, users, processes
- **Realistic network topology** - Firewalls, DMZ zones, internal networks
- **Network routing** - Systems can only communicate if routes exist
- **Firewall rules** - Certain ports are blocked from external access
- **Running services** - Detected through port scanning
- **Vulnerable configurations** - Weak passwords, exposed config files, command history
- **Flags** - Your objective is to reach the target system and find the flag

## Strategy

1. **Reconnaissance** - Use `nmap` to discover hosts and open ports
2. **Enumeration** - Identify services, users, and potential vulnerabilities
3. **Exploitation** - Find credentials in config files, bash history, etc.
4. **Lateral Movement** - Use compromised systems to access deeper into the network
5. **Objective** - Reach the target system and retrieve the flag

Good luck, hacker!
