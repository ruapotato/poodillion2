#!/usr/bin/env python3
"""
Game scenarios for Poodillion 2
Each scenario creates a realistic network topology with multiple systems
"""

from core.system import UnixSystem
from core.network_adapter import NetworkAdapter


def create_scenario_zero():
    """
    Scenario Zero: SSH Training Network
    - Simple flat network with multiple systems
    - All systems have root/root credentials
    - Learn to SSH between systems
    - Practice basic Unix commands across multiple hosts
    """
    network = NetworkAdapter()

    # Attacker system (your machine)
    attacker = UnixSystem('training-box', '192.168.1.100')
    attacker.add_network(network)

    # Create training notes
    attacker.vfs.create_file(
        '/root/README.txt',
        0o644, 0, 0,
        b'=== SSH TRAINING SCENARIO ===\n\n'
        b'Welcome to Poodillion 2!\n\n'
        b'This scenario teaches you how to SSH between systems.\n'
        b'All systems on this network:\n'
        b'  - training-box (192.168.1.100) <- YOU ARE HERE\n'
        b'  - router (192.168.1.1)\n'
        b'  - server-alpha (192.168.1.10)\n'
        b'  - server-beta (192.168.1.20)\n'
        b'  - server-gamma (192.168.1.30)\n\n'
        b'All systems have login: root/root\n\n'
        b'MISSION:\n'
        b'1. Use "ping" to verify connectivity\n'
        b'2. Use "ssh <ip>" to connect to each server\n'
        b'3. Find the flag file on server-gamma\n'
        b'4. Practice navigating between systems\n\n'
        b'TIPS:\n'
        b'  - Type "exit" to close SSH connection and return\n'
        b'  - You can SSH from any system to any other system\n'
        b'  - Try: ssh 192.168.1.10\n'
        b'  - Try: ssh 192.168.1.1\n\n'
        b'ADVANCED:\n'
        b'  - Multi-hop SSH: ssh to A, then ssh to B, then ssh to C\n'
        b'  - Type "exit" repeatedly to return through the chain\n'
        b'  - Try "shutdown" to take a system offline\n'
        b'  - After shutdown, ping/ssh will fail until system reboots\n\n'
        b'Have fun exploring!\n',
        1
    )

    # Router with routing between networks
    router = UnixSystem('router', '192.168.1.1')
    router.add_network(network)
    router.vfs.create_file(
        '/root/router-info.txt',
        0o644, 0, 0,
        b'This is the network router.\n'
        b'All traffic flows through here.\n\n'
        b'Connected systems:\n'
        b'  192.168.1.10 - server-alpha\n'
        b'  192.168.1.20 - server-beta\n'
        b'  192.168.1.30 - server-gamma\n'
        b'  192.168.1.100 - training-box\n',
        1
    )

    # Server Alpha
    server_alpha = UnixSystem('server-alpha', '192.168.1.10')
    server_alpha.add_network(network)
    server_alpha.vfs.create_file(
        '/root/welcome.txt',
        0o644, 0, 0,
        b'Welcome to Server Alpha!\n\n'
        b'You have successfully SSH\'d into your first remote system.\n\n'
        b'Try these commands:\n'
        b'  - ls -la /root\n'
        b'  - ps -f\n'
        b'  - cat /etc/hostname\n'
        b'  - ifconfig\n\n'
        b'When you\'re done, type "exit" to return to your previous system.\n',
        1
    )
    server_alpha.vfs.create_file(
        '/var/log/access.log',
        0o644, 0, 0,
        b'[LOG] Server Alpha - Web service logs\n'
        b'[2025-01-15 10:23:45] GET /index.html - 200 OK\n'
        b'[2025-01-15 10:24:12] GET /admin.php - 403 Forbidden\n',
        1
    )

    # Server Beta
    server_beta = UnixSystem('server-beta', '192.168.1.20')
    server_beta.add_network(network)
    server_beta.vfs.create_file(
        '/root/data.txt',
        0o644, 0, 0,
        b'Server Beta - Database Server\n\n'
        b'This server hosts the main database.\n\n'
        b'Database Info:\n'
        b'  Host: localhost\n'
        b'  Port: 3306\n'
        b'  Name: training_db\n\n'
        b'HINT: The flag is not here. Try server-gamma (192.168.1.30)\n',
        1
    )
    server_beta.spawn_service('mysqld', ['service', 'database'], uid=27)

    # Server Gamma - has the flag
    server_gamma = UnixSystem('server-gamma', '192.168.1.30')
    server_gamma.add_network(network)
    server_gamma.vfs.create_file(
        '/root/flag.txt',
        0o644, 0, 0,
        b'*************************************\n'
        b'*                                   *\n'
        b'*  CONGRATULATIONS!                 *\n'
        b'*                                   *\n'
        b'*  You have completed SSH training  *\n'
        b'*                                   *\n'
        b'*  FLAG{you_are_now_an_ssh_master}  *\n'
        b'*                                   *\n'
        b'*************************************\n\n'
        b'You have learned how to:\n'
        b'  [x] Navigate a virtual network\n'
        b'  [x] Use SSH to connect to remote systems\n'
        b'  [x] Execute commands on multiple hosts\n'
        b'  [x] Exit SSH sessions and return\n\n'
        b'Ready for real hacking scenarios? Try Scenario 1!\n',
        1
    )
    server_gamma.vfs.create_file(
        '/var/www/secret.txt',
        0o644, 33, 33,
        b'SECRET: The admin password is "admin123"\n',
        1
    )
    server_gamma.spawn_service('apache2', ['service', 'webserver'], uid=33)

    # Layer-2 Network Connectivity (full mesh for training)
    systems = [
        ('192.168.1.100', attacker),
        ('192.168.1.1', router),
        ('192.168.1.10', server_alpha),
        ('192.168.1.20', server_beta),
        ('192.168.1.30', server_gamma),
    ]

    # Create full mesh connectivity (everyone can reach everyone)
    for ip1, _ in systems:
        for ip2, _ in systems:
            if ip1 != ip2:
                network.add_route(ip1, ip2)

    # Configure routing tables on all routers
    network._configure_routing_tables()

    return attacker, network, {
        'title': 'Scenario 0: SSH Training',
        'description': 'Learn to navigate between systems using SSH',
        'objective': 'SSH to all servers and find the flag on server-gamma',
        'difficulty': 'Tutorial',
        'systems': [attacker, router, server_alpha, server_beta, server_gamma],
        'hints': [
            'Start by reading /root/README.txt',
            'Use: ssh 192.168.1.10',
            'Type "exit" to close SSH connection',
            'The flag is on 192.168.1.30',
        ]
    }


def create_beginner_scenario():
    """
    Beginner: Simple Corporate Network
    - Attacker on public internet (10.0.0.0/24)
    - Router with IP forwarding between networks
    - One web server behind router (192.168.1.0/24)
    """
    network = NetworkAdapter()

    # Attacker system (your machine)
    attacker = UnixSystem('kali-box', '10.0.0.100')
    attacker.add_network(network)
    attacker.default_gateway = '10.0.0.1'  # Set default gateway

    # Create hacking tools and notes
    attacker.vfs.create_file(
        '/root/notes.txt',
        0o644, 0, 0,
        b'Target Network: 192.168.1.0/24\n'
        b'Objective: Compromise the web server and find the flag\n'
        b'Gateway: 10.0.0.1 (routes to 192.168.1.1)\n'
        b'Target: 192.168.1.50\n\n'
        b'Try: ping 192.168.1.50\n'
        b'Try: nmap 192.168.1.50\n',
        1
    )

    # Firewall/Router with 2 interfaces (gateway between internet and internal network)
    firewall = UnixSystem('firewall', {
        'eth0': '10.0.0.1',       # External (internet-facing)
        'eth1': '192.168.1.1'     # Internal (corporate LAN)
    })
    firewall.ip_forward = True  # Enable routing between networks
    firewall.add_network(network)
    firewall.vfs.write_file('/etc/hostname', b'firewall\n', 1)

    # Add some firewall config files
    firewall.vfs.create_file(
        '/etc/firewall.conf',
        0o644, 0, 0,
        b'# Firewall Rules\n'
        b'ALLOW 80/tcp from any\n'
        b'ALLOW 443/tcp from any\n'
        b'ALLOW 22/tcp from 10.0.0.0/8\n'
        b'DENY all\n',
        1
    )

    firewall.spawn_service('iptables', ['service', 'firewall'], uid=0)

    # Web Server
    webserver = UnixSystem('web-01', '192.168.1.50')
    webserver.default_gateway = '192.168.1.1'
    webserver.add_network(network)

    # Add users
    webserver.add_user('webadmin', 'password123', 1001, '/home/webadmin')
    webserver.add_user('developer', 'dev2024', 1002, '/home/developer')

    # Add vulnerable files
    webserver.create_vulnerable_file(
        '/home/webadmin/.bash_history',
        b'ls -la\n'
        b'sudo systemctl restart apache2\n'
        b'mysql -u root -pMyS3cr3tP@ss\n'
        b'cat /var/www/html/admin.php\n'
        b'chmod 777 /var/www/uploads\n',
        hint='Command history contains credentials'
    )

    webserver.vfs.create_file(
        '/var/www/config.php',
        0o644, 33, 33,
        b'<?php\n'
        b'$db_host = "localhost";\n'
        b'$db_user = "root";\n'
        b'$db_pass = "MyS3cr3tP@ss";\n'
        b'$db_name = "webapp";\n'
        b'?>\n',
        1
    )

    webserver.vfs.create_file(
        '/var/www/html/index.html',
        0o644, 33, 33,
        b'<html><body><h1>Welcome to Corporate Web Server</h1></body></html>\n',
        1
    )

    webserver.vfs.create_file(
        '/root/flag.txt',
        0o600, 0, 0,
        b'FLAG{congratulations_you_hacked_the_webserver}\n',
        1
    )

    # Spawn services
    webserver.spawn_service('apache2', ['service', 'webserver', 'vulnerable'], uid=33)
    webserver.spawn_service('mysqld', ['service', 'database'], uid=27)
    webserver.spawn_service('sshd', ['service', 'ssh'], uid=0)

    # Layer-2 Network Connectivity (who can directly communicate)
    # Attacker <-> Router (external interface)
    network.add_route('10.0.0.100', '10.0.0.1')
    network.add_route('10.0.0.1', '10.0.0.100')

    # Router (internal) <-> Web Server
    network.add_route('192.168.1.1', '192.168.1.50')
    network.add_route('192.168.1.50', '192.168.1.1')

    # Multi-hop routing will automatically work because:
    # - Attacker -> Router external (10.0.0.1)
    # - Router forwards (ip_forward=True)
    # - Router internal (192.168.1.1) -> Webserver

    # Firewall rules - allow web traffic, block SSH from outside
    network.add_firewall_rule('192.168.1.50', 'DENY', 22)  # Block SSH from outside

    # Configure routing tables
    network._configure_routing_tables()

    return attacker, network, {
        'title': 'Beginner: Simple Corporate Hack',
        'description': 'Compromise a web server behind a router/firewall',
        'objective': 'Find the flag in /root/flag.txt on the web server',
        'difficulty': 'Easy',
        'systems': [attacker, firewall, webserver],
        'hints': [
            'Try: ping 192.168.1.50 (tests multi-hop routing)',
            'Try: nmap 192.168.1.50',
            'Try: cat /proc/net/arp (see ARP cache)',
            'Try: cat /proc/net/route (see routing table)',
        ]
    }


def create_intermediate_scenario():
    """
    Intermediate: Corporate DMZ
    - Attacker on internet (10.0.0.0/24)
    - Router with 3 interfaces (external, DMZ, internal)
    - Web server in DMZ (192.168.100.0/24)
    - Database server in internal network (192.168.10.0/24)
    - Jump host for internal access
    """
    network = NetworkAdapter()

    # Attacker
    attacker = UnixSystem('kali-box', '10.0.0.100')
    attacker.default_gateway = '10.0.0.1'
    attacker.add_network(network)

    attacker.vfs.create_file(
        '/root/notes.txt',
        0o644, 0, 0,
        b'Target: Corporate Network\n'
        b'External: 10.0.0.0/24\n'
        b'DMZ: 192.168.100.0/24\n'
        b'Internal: 192.168.10.0/24\n'
        b'Objective: Access the internal database and exfiltrate data\n\n'
        b'Gateway: 10.0.0.1\n'
        b'Strategy: Compromise DMZ web server, then pivot to internal network\n',
        1
    )

    # Firewall/Router with 3 interfaces
    firewall = UnixSystem('corp-firewall', {
        'eth0': '10.0.0.1',         # External (internet)
        'eth1': '192.168.100.1',    # DMZ
        'eth2': '192.168.10.1'      # Internal LAN
    })
    firewall.ip_forward = True  # Enable routing
    firewall.add_network(network)
    firewall.spawn_service('iptables', ['service', 'firewall'], uid=0)

    # DMZ Web Server
    webserver = UnixSystem('dmz-web-01', '192.168.100.10')
    webserver.default_gateway = '192.168.100.1'
    webserver.add_network(network)
    webserver.add_user('webadmin', 'admin123', 1001, '/home/webadmin')

    webserver.vfs.create_file(
        '/var/www/.git/config',
        0o644, 33, 33,
        b'[core]\n'
        b'repositoryformatversion = 0\n'
        b'[remote "origin"]\n'
        b'url = ssh://git@192.168.10.20:/repos/webapp.git\n',
        1
    )

    webserver.vfs.create_file(
        '/home/webadmin/.ssh/id_rsa',
        0o600, 1001, 1001,
        b'-----BEGIN RSA PRIVATE KEY-----\n'
        b'[SSH PRIVATE KEY FOR INTERNAL ACCESS]\n'
        b'This key provides access to 192.168.10.20\n'
        b'-----END RSA PRIVATE KEY-----\n',
        1
    )

    webserver.spawn_service('apache2', ['service', 'webserver', 'vulnerable'], uid=33)
    webserver.spawn_service('sshd', ['service', 'ssh'], uid=0)

    # Internal Jump Host
    jumphost = UnixSystem('jump-01', '192.168.10.20')
    jumphost.default_gateway = '192.168.10.1'
    jumphost.add_network(network)
    jumphost.add_user('sysadmin', 'sysPass2024', 1001, '/home/sysadmin')

    jumphost.vfs.create_file(
        '/home/sysadmin/.ssh/authorized_keys',
        0o600, 1001, 1001,
        b'ssh-rsa AAAAB3... webadmin@dmz-web-01\n',
        1
    )

    jumphost.spawn_service('sshd', ['service', 'ssh'], uid=0)

    # Internal Database Server
    dbserver = UnixSystem('db-01', '192.168.10.50')
    dbserver.default_gateway = '192.168.10.1'
    dbserver.add_network(network)
    dbserver.add_user('dba', 'dba_secure_2024', 1001, '/home/dba')

    dbserver.vfs.create_file(
        '/var/lib/mysql/customers.sql',
        0o640, 27, 27,
        b'-- Customer Database\n'
        b'CREATE TABLE customers (\n'
        b'  id INT,\n'
        b'  name VARCHAR(100),\n'
        b'  email VARCHAR(100),\n'
        b'  credit_card VARCHAR(16)\n'
        b');\n'
        b'INSERT INTO customers VALUES (1, "John Doe", "john@example.com", "4532-1234-5678-9012");\n'
        b'-- FLAG{you_accessed_the_internal_database}\n',
        1
    )

    dbserver.spawn_service('mysqld', ['service', 'database'], uid=27)
    dbserver.spawn_service('sshd', ['service', 'ssh'], uid=0)

    # Layer-2 Network Connectivity
    # Attacker <-> Router (external)
    network.add_route('10.0.0.100', '10.0.0.1')
    network.add_route('10.0.0.1', '10.0.0.100')

    # Router (DMZ) <-> DMZ Web Server
    network.add_route('192.168.100.1', '192.168.100.10')
    network.add_route('192.168.100.10', '192.168.100.1')

    # Router (internal) <-> Jump Host
    network.add_route('192.168.10.1', '192.168.10.20')
    network.add_route('192.168.10.20', '192.168.10.1')

    # Jump Host <-> Database Server (internal network)
    network.add_route('192.168.10.20', '192.168.10.50')
    network.add_route('192.168.10.50', '192.168.10.20')

    # Multi-hop routing will work automatically:
    # - Attacker -> Router external (10.0.0.1)
    # - Router forwards to DMZ (192.168.100.1)
    # - DMZ can access internal through router (192.168.10.1)

    # Firewall rules - block direct external->internal access
    # (attacker must pivot through DMZ)

    # Configure routing tables
    network._configure_routing_tables()

    return attacker, network, {
        'title': 'Intermediate: Corporate DMZ Breach',
        'description': 'Pivot through DMZ to access internal database',
        'objective': 'Access /var/lib/mysql/customers.sql on the internal database server',
        'difficulty': 'Medium',
        'systems': [attacker, firewall, webserver, jumphost, dbserver]
    }


def create_advanced_scenario():
    """
    Advanced: Multi-Site Corporate Network
    - Multiple locations
    - VPN connections
    - Segmented networks
    - Multiple attack vectors
    """
    network = NetworkAdapter()

    # Attacker
    attacker = UnixSystem('kali-box', '10.0.0.100')
    attacker.add_network(network)

    attacker.vfs.create_file(
        '/root/mission.txt',
        0o644, 0, 0,
        b'MISSION BRIEFING\n'
        b'================\n'
        b'Target: MegaCorp International\n'
        b'HQ Network: 192.168.1.0/24\n'
        b'Branch Office: 192.168.2.0/24\n'
        b'Partner Network: 192.168.3.0/24\n\n'
        b'Objective: Gain access to the CEO\'s email server (192.168.1.100)\n'
        b'           and retrieve sensitive communications\n\n'
        b'Known info:\n'
        b'- Public website at 192.168.1.50\n'
        b'- VPN gateway at 192.168.1.1\n'
        b'- Branch office has weaker security\n',
        1
    )

    # HQ Network Router/Firewall with multi-interface
    hq_firewall = UnixSystem('hq-firewall', {
        'eth0': '10.0.0.1',       # External (internet)
        'eth1': '192.168.1.1'     # Internal HQ network
    })
    hq_firewall.ip_forward = True
    hq_firewall.add_network(network)
    hq_firewall.spawn_service('iptables', ['service', 'firewall'], uid=0)
    hq_firewall.spawn_service('openvpn', ['service', 'vpn'], uid=0)

    hq_web = UnixSystem('hq-web', '192.168.1.50')
    hq_web.default_gateway = '192.168.1.1'
    hq_web.add_network(network)
    hq_web.add_user('webdev', 'Dev123!', 1001, '/home/webdev')
    hq_web.spawn_service('apache2', ['service', 'webserver', 'vulnerable'], uid=33)
    hq_web.spawn_service('sshd', ['service', 'ssh'], uid=0)

    hq_web.vfs.create_file(
        '/var/www/.env',
        0o644, 33, 33,
        b'DB_HOST=192.168.1.200\n'
        b'DB_USER=webapp\n'
        b'DB_PASS=WebApp2024!\n'
        b'SMTP_HOST=192.168.1.100\n'
        b'ADMIN_EMAIL=admin@megacorp.com\n',
        1
    )

    hq_mail = UnixSystem('mail-server', '192.168.1.100')
    hq_mail.default_gateway = '192.168.1.1'
    hq_mail.add_network(network)
    hq_mail.add_user('postmaster', 'MailSecure2024', 1001, '/home/postmaster')

    hq_mail.vfs.create_file(
        '/var/mail/ceo/inbox/secret.eml',
        0o600, 0, 0,
        b'From: cfo@megacorp.com\n'
        b'To: ceo@megacorp.com\n'
        b'Subject: Q4 Merger - CONFIDENTIAL\n\n'
        b'The acquisition is proceeding as planned.\n'
        b'Wire transfer details:\n'
        b'Account: 1234-5678-9012\n'
        b'Amount: $50M\n\n'
        b'FLAG{you_have_compromised_executive_communications}\n',
        1
    )

    hq_mail.spawn_service('postfix', ['service', 'mail'], uid=0)
    hq_mail.spawn_service('sshd', ['service', 'ssh'], uid=0)

    # Branch Office Network (weaker security - entry point)
    branch_firewall = UnixSystem('branch-firewall', {
        'eth0': '10.0.0.2',       # External (internet)
        'eth1': '192.168.2.1'     # Branch LAN
    })
    branch_firewall.ip_forward = True
    branch_firewall.add_network(network)
    branch_firewall.spawn_service('iptables', ['service', 'firewall'], uid=0)

    branch_workstation = UnixSystem('branch-pc-05', '192.168.2.50')
    branch_workstation.default_gateway = '192.168.2.1'
    branch_workstation.add_network(network)
    branch_workstation.add_user('employee', 'Summer2024', 1001, '/home/employee')

    branch_workstation.vfs.create_file(
        '/home/employee/vpn-config.ovpn',
        0o644, 1001, 1001,
        b'# OpenVPN Config for HQ Access\n'
        b'remote 192.168.1.1 1194\n'
        b'auth-user-pass /home/employee/.vpn-creds\n',
        1
    )

    branch_workstation.vfs.create_file(
        '/home/employee/.vpn-creds',
        0o600, 1001, 1001,
        b'vpnuser\n'
        b'VPN_P@ssw0rd_2024\n',
        1
    )

    branch_workstation.spawn_service('sshd', ['service', 'ssh', 'vulnerable'], uid=0)

    # Partner Network (trusted but external)
    partner_server = UnixSystem('partner-api', '192.168.3.10')
    partner_server.default_gateway = '10.0.0.3'  # Separate network segment
    partner_server.add_network(network)
    partner_server.add_user('apiuser', 'api_key_2024', 1001, '/home/apiuser')
    partner_server.spawn_service('nginx', ['service', 'webserver'], uid=33)
    partner_server.spawn_service('sshd', ['service', 'ssh'], uid=0)

    # Layer-2 Network Connectivity - complex multi-site topology
    # Attacker <-> Internet
    network.add_route('10.0.0.100', '10.0.0.1')
    network.add_route('10.0.0.100', '10.0.0.2')
    network.add_route('10.0.0.1', '10.0.0.100')
    network.add_route('10.0.0.2', '10.0.0.100')

    # HQ Firewall (internal) <-> HQ Systems
    network.add_route('192.168.1.1', '192.168.1.50')
    network.add_route('192.168.1.50', '192.168.1.1')
    network.add_route('192.168.1.1', '192.168.1.100')
    network.add_route('192.168.1.100', '192.168.1.1')

    # HQ internal connectivity (web <-> mail)
    network.add_route('192.168.1.50', '192.168.1.100')
    network.add_route('192.168.1.100', '192.168.1.50')

    # Branch Firewall (internal) <-> Branch Workstation
    network.add_route('192.168.2.1', '192.168.2.50')
    network.add_route('192.168.2.50', '192.168.2.1')

    # Partner connectivity (simulated via internet backbone)
    network.add_route('10.0.0.1', '192.168.3.10')
    network.add_route('192.168.3.10', '10.0.0.1')

    # Multi-hop routing happens automatically via ip_forward=True

    # Firewall rules
    network.add_firewall_rule('192.168.1.100', 'DENY', 22)  # Mail server SSH blocked from outside
    network.add_firewall_rule('192.168.1.100', 'DENY', 25)  # SMTP blocked from outside

    # Configure routing tables
    network._configure_routing_tables()

    return attacker, network, {
        'title': 'Advanced: Multi-Site Enterprise Compromise',
        'description': 'Navigate complex network topology to reach executive mail server',
        'objective': 'Read the CEO\'s confidential email at /var/mail/ceo/inbox/secret.eml',
        'difficulty': 'Hard',
        'systems': [attacker, hq_firewall, hq_web, hq_mail, branch_firewall, branch_workstation, partner_server]
    }


# Scenario registry
SCENARIOS = {
    '0': create_scenario_zero,
    '1': create_beginner_scenario,
    '2': create_intermediate_scenario,
    '3': create_advanced_scenario,
}

# Scenario metadata (for menu display without creating full scenarios)
SCENARIO_INFO = {
    '0': {
        'title': 'Scenario 0: SSH Training',
        'description': 'Learn to navigate between systems using SSH',
        'difficulty': 'Tutorial',
    },
    '1': {
        'title': 'Beginner: Simple Corporate Hack',
        'description': 'Compromise a web server behind a basic firewall',
        'difficulty': 'Easy',
    },
    '2': {
        'title': 'Intermediate: Corporate DMZ Breach',
        'description': 'Pivot through DMZ to access internal database',
        'difficulty': 'Medium',
    },
    '3': {
        'title': 'Advanced: Multi-Site Enterprise Compromise',
        'description': 'Navigate complex network topology to reach executive mail server',
        'difficulty': 'Hard',
    },
}


def list_scenarios():
    """Return list of available scenarios"""
    scenarios = []

    for key, info in SCENARIO_INFO.items():
        scenarios.append({
            'key': key,
            **info
        })

    return scenarios
