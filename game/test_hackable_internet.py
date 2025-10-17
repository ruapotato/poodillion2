#!/usr/bin/env python3
"""
Create a fun hackable internet with cool websites
"""

from core.system import UnixSystem
from core.network_adapter import NetworkAdapter


def create_hackable_internet():
    """Build a fun hackable internet"""

    print("="*70)
    print("BUILDING THE HACKABLE INTERNET OF 1990")
    print("="*70)

    network = NetworkAdapter()

    print("""
    Creating a retro internet full of secrets and vulnerabilities...

    🌐 THE INTERNET TOPOLOGY 🌐

    [Internet Backbone - 8.8.0.0/16]
         dns.internet (8.8.8.8)         [DNS Server]
         isp-router (8.8.0.1)           [ISP Router - connects everything]

    [Corporate Networks]
         megacorp.com (200.1.1.100)     [Fortune 500 company - trade secrets!]
         cyberbank.net (200.2.2.100)    [Online bank - $$$]
         darpa.mil (200.3.3.100)        [Military network - TOP SECRET]

    [Underground Sites]
         hackerz.underground (201.1.1.100)    [Elite hacker BBS]
         darkweb.onion (201.2.2.100)          [Underground marketplace]
         freespeech.org (201.3.3.100)         [Anonymous forum]

    [Fun Sites]
         geocities.com (202.1.1.100)    [Personal websites with bad security]
         angelfire.com (202.2.2.100)    [More terrible 90s sites]
         altavista.com (202.3.3.100)    [Search engine (pre-Google)]

    [Educational]
         mit.edu (203.1.1.100)          [University - research papers]
         library.gov (203.2.2.100)      [Public library]

    [Your System]
         laptop.home (192.168.1.100)    [Your hacker lair]

    """)

    # DNS Server
    dns_server = UnixSystem('dns.internet', '8.8.8.8')

    # ISP Router (connects everyone)
    isp_router = UnixSystem('isp-router', '8.8.0.1')
    isp_router.ip_forward = True

    # Your hacker laptop
    laptop = UnixSystem('laptop.home', '192.168.1.100')
    laptop.default_gateway = '8.8.0.1'

    # CORPORATE SITES (high security, valuable data)
    megacorp = UnixSystem('megacorp.com', '200.1.1.100')
    megacorp.default_gateway = '8.8.0.1'

    cyberbank = UnixSystem('cyberbank.net', '200.2.2.100')
    cyberbank.default_gateway = '8.8.0.1'

    darpa = UnixSystem('darpa.mil', '200.3.3.100')
    darpa.default_gateway = '8.8.0.1'

    # UNDERGROUND SITES (hacker havens)
    hackerz_bbs = UnixSystem('hackerz.underground', '201.1.1.100')
    hackerz_bbs.default_gateway = '8.8.0.1'

    darkweb = UnixSystem('darkweb.onion', '201.2.2.100')
    darkweb.default_gateway = '8.8.0.1'

    freespeech = UnixSystem('freespeech.org', '201.3.3.100')
    freespeech.default_gateway = '8.8.0.1'

    # FUN 90s SITES (low security, lots of vulnerabilities)
    geocities = UnixSystem('geocities.com', '202.1.1.100')
    geocities.default_gateway = '8.8.0.1'

    angelfire = UnixSystem('angelfire.com', '202.2.2.100')
    angelfire.default_gateway = '8.8.0.1'

    altavista = UnixSystem('altavista.com', '202.3.3.100')
    altavista.default_gateway = '8.8.0.1'

    # EDUCATIONAL SITES
    mit = UnixSystem('mit.edu', '203.1.1.100')
    mit.default_gateway = '8.8.0.1'

    library = UnixSystem('library.gov', '203.2.2.100')
    library.default_gateway = '8.8.0.1'

    # Collect all systems
    systems = {
        'dns': dns_server,
        'isp': isp_router,
        'laptop': laptop,
        'megacorp': megacorp,
        'cyberbank': cyberbank,
        'darpa': darpa,
        'hackerz': hackerz_bbs,
        'darkweb': darkweb,
        'freespeech': freespeech,
        'geocities': geocities,
        'angelfire': angelfire,
        'altavista': altavista,
        'mit': mit,
        'library': library,
    }

    # Add to network
    for sys in systems.values():
        sys.add_network(network)

    # Connect everyone to ISP router (star topology)
    for name, sys in systems.items():
        if name not in ['isp', 'dns']:
            network.add_route(sys.ip, '8.8.0.1')
            network.add_route('8.8.0.1', sys.ip)

    # DNS to ISP
    network.add_route('8.8.8.8', '8.8.0.1')
    network.add_route('8.8.0.1', '8.8.8.8')

    print("Booting all systems...")
    for sys in systems.values():
        sys.boot(verbose=False)
        sys.login('root', 'root')

    print("✓ All systems online\n")

    # CREATE AWESOME CONTENT
    print("Creating website content and secrets...")

    # === MEGACORP ===
    megacorp.vfs.mkdir('/var/www', 0o755, 0, 0, 1)
    megacorp.vfs.create_file('/var/www/index.html', 0o644, 0, 0, b"""
<html><body>
<h1>MEGACORP INTERNATIONAL</h1>
<p>World's leading manufacturer of questionable products!</p>
<p>Stock price: $999.99 (INSIDER INFO: About to crash due to scandal)</p>
<a href="/secrets">Employee Portal</a>
</body></html>
""", 1)

    megacorp.vfs.create_file('/var/www/secrets', 0o600, 0, 0, b"""
MEGACORP CONFIDENTIAL - DO NOT DISTRIBUTE

Project Codename: SKYNET
Budget: $500 million
Status: ACTIVE

We are developing an AI that will replace all human workers.
Launch date: December 31, 1999 (Y2K cover story)

CEO's password: password123
CFO's password: admin
""", 1)

    megacorp.vfs.create_file('/home/ceo/.bash_history', 0o600, 0, 0, b"""
ssh admin@darpa.mil
cat /classified/alien_tech.txt
rm -rf evidence/
scp offshore_accounts.xlsx cayman.islands.bank
echo "I love embezzling" > diary.txt
""", 1)

    # === CYBERBANK ===
    cyberbank.vfs.mkdir('/var/www', 0o755, 0, 0, 1)
    cyberbank.vfs.create_file('/var/www/index.html', 0o644, 0, 0, b"""
<html><body>
<h1>CYBERBANK.NET - Your Money is Safe! (LOL)</h1>
<p>Welcome to the FUTURE of banking!</p>
<p>Our security is UNBREAKABLE! (We use ROT13 encryption!)</p>
<form action="/login">
    Username: <input name="user"><br>
    Password: <input name="pass"><br>
</form>
</body></html>
""", 1)

    cyberbank.vfs.create_file('/etc/passwords.txt', 0o644, 0, 0, b"""
# TOTALLY SECURE PASSWORD FILE - ENCRYPTED WITH ROT13!
admin:nqzva123
root:ebbg
billgates:zbarl123
hackerman:V_YBIR_PUNFR_ONAX
""", 1)

    cyberbank.vfs.create_file('/var/accounts/balances.db', 0o600, 0, 0, b"""
ACCOUNT_DATABASE_v1.0

acc_12345: $1,000,000.00 (billgates)
acc_99999: $50,000,000.00 (admin_slush_fund)
acc_00001: $0.25 (your_account_lol)
acc_31337: $999,999,999.99 (HACKER_BONUS_ACCOUNT)
""", 1)

    # === DARPA (Military) ===
    darpa.vfs.mkdir('/classified', 0o700, 0, 0, 1)
    darpa.vfs.create_file('/classified/README.txt', 0o600, 0, 0, b"""
DARPA CLASSIFIED NETWORK
TOP SECRET // COSMIC // MAJIC

This system contains information regarding:
- Alien technology recovered from Roswell
- Time travel experiments
- The REAL purpose of the internet (hint: it's not cat videos)

Unauthorized access is punishable by memory erasure.

If you can read this, congrats! You're elite!
""", 1)

    darpa.vfs.create_file('/classified/arpanet_origins.txt', 0o600, 0, 0, b"""
ARPANET - THE TRUTH

The internet was NOT created for military communications.

It was created to distribute memes and argue about text editors.

Vi vs Emacs has been raging since 1976.

This war will never end.
""", 1)

    # Add firewall to protect the good stuff
    darpa.firewall_rules.append({
        'chain': 'INPUT',
        'protocol': 'tcp',
        'port': 22,
        'action': 'DROP',
        'source': '192.168.0.0/16'  # Block home networks
    })

    # === HACKERZ BBS ===
    hackerz_bbs.vfs.mkdir('/bbs', 0o755, 0, 0, 1)
    hackerz_bbs.vfs.create_file('/bbs/welcome.txt', 0o644, 0, 0, b"""
+===========================================================+
|  H4CK3RZ UNDERGROUND BBS - ELITE ONLY - EST. 1985        |
+===========================================================+

Welcome, l33t h4x0r!

Message Boards:
  1. Phreaking & Telco Hacking
  2. Zero-Day Exploits
  3. Credit Card Numbers (DISCLAIMER: for educational purposes)
  4. How to Hack Gibson (IT'S A UNIX SYSTEM!)
  5. Where to buy pizza with Bitcoin (coming soon in 2009)

Latest News:
- New exploit for Windows 3.1 buffer overflow
- AOL free trial CD generator released
- Hacker "Crash Override" arrested (Free Kevin!)

Type 'help' for commands
""", 1)

    hackerz_bbs.vfs.create_file('/bbs/exploits.txt', 0o644, 0, 0, b"""
PUBLIC EXPLOITS DATABASE

[1995-001] MegaCorp CEO Password: password123
[1995-002] CyberBank ROT13 "encryption" (LOL)
[1995-003] Geocities admin:admin (no joke)
[1995-004] DARPA backdoor at port 31337

Remember: With great power comes great responsibility!
(But mainly great power)
""", 1)

    # === GEOCITIES (So insecure it's funny) ===
    geocities.vfs.mkdir('/users', 0o777, 0, 0, 1)  # World writable!
    geocities.vfs.create_file('/users/coolkid99/index.html', 0o644, 0, 0, b"""
<html>
<body bgcolor="black" text="lime">
<center>
<h1><blink>WELCOME TO COOLKID99'S HOMEPAGE</blink></h1>
<marquee>THIS SITE IS BEST VIEWED IN NETSCAPE NAVIGATOR</marquee>
<img src="under_construction.gif">
<p>Visitor count: 42</p>
<p>Sign my guestbook!</p>
<p>My password is 'password' but don't tell anyone!</p>
<img src="geocities.gif">
</center>
</body>
</html>
""", 1)

    geocities.vfs.create_file('/admin/passwords.txt', 0o644, 0, 0, b"""
# Geocities Admin Passwords (stored in plaintext since 1994)
admin:admin
root:root
webmaster:webmaster
coolkid99:password
hackerman:hunter2 (you can't see this, it shows as *******)
""", 1)

    # === DARKWEB ===
    darkweb.vfs.create_file('/var/www/index.html', 0o644, 0, 0, b"""
<html><body bgcolor="black" text="red">
<h1>WELCOME TO THE DARKWEB</h1>
<p>You have accessed the ILLEGAL zone of the internet!</p>

<h2>Services Available:</h2>
- Rare Pepe Trading Cards
- Unlimited AOL Trial CDs
- Hacker Tools (hacking_tool.exe - totally not a virus)
- Secrets the Government Doesn't Want You to Know
- The REAL recipe for Coca-Cola

<p>To access the secret marketplace, you need the password.</p>
<p>Hint: It's in the HTML source code below</p>

<!-- Password: hacktheplanet1995 -->
</body></html>
""", 1)

    # === MIT ===
    mit.vfs.create_file('/research/ai_papers.txt', 0o644, 0, 0, b"""
MIT ARTIFICIAL INTELLIGENCE LAB

Recent Papers:
- "Why Lisp is the Perfect Language" (Spoiler: It's not)
- "Neural Networks: Will They Ever Work?" (Spoiler: Yes, in 2012)
- "Can Computers Think?" (Spoiler: They can, but they choose not to)

Fun Fact: The password to the lab is 'stallman'
but he'll give you a 4-hour lecture about free software first.
""", 1)

    # CREATE DNS ZONES
    print("Setting up DNS...")

    dns_zones = """# HACKABLE INTERNET DNS ZONES

# Corporate
megacorp.com A 200.1.1.100
www.megacorp.com A 200.1.1.100
cyberbank.net A 200.2.2.100
www.cyberbank.net A 200.2.2.100
darpa.mil A 200.3.3.100

# Underground
hackerz.underground A 201.1.1.100
darkweb.onion A 201.2.2.100
freespeech.org A 201.3.3.100

# Fun 90s sites
geocities.com A 202.1.1.100
www.geocities.com A 202.1.1.100
angelfire.com A 202.2.2.100
altavista.com A 202.3.3.100

# Educational
mit.edu A 203.1.1.100
library.gov A 203.2.2.100

# Infrastructure
dns.internet A 8.8.8.8
laptop.home A 192.168.1.100
"""

    # Create DNS database on all systems
    for sys in systems.values():
        sys.vfs.create_file('/var/run/named.db', 0o644, 0, 0, dns_zones.encode(), 1)
        sys.vfs.create_file('/etc/hosts', 0o644, 0, 0, dns_zones.encode(), 1)

    print("✓ DNS configured\n")

    # PRINT HACKING GUIDE
    print("="*70)
    print("🎮 WELCOME TO THE HACKABLE INTERNET! 🎮")
    print("="*70)

    print("""
    YOUR MISSION: Explore the internet and find secrets!

    💰 CORPORATE TARGETS (High Value):
    ├─ megacorp.com (200.1.1.100)
    │  └─ Find the CEO's dark secrets
    │  └─ Insider trading info worth millions!
    │
    ├─ cyberbank.net (200.2.2.100)
    │  └─ "Encrypted" with ROT13 (lol)
    │  └─ Find the $999M hacker bonus account
    │
    └─ darpa.mil (200.3.3.100)
       └─ TOP SECRET military files
       └─ Firewall protected! (Can you bypass it?)

    🌐 UNDERGROUND SITES:
    ├─ hackerz.underground (201.1.1.100)
    │  └─ Elite hacker BBS
    │  └─ Public exploit database
    │
    └─ darkweb.onion (201.2.2.100)
       └─ Secret marketplace
       └─ Password hidden in HTML comments!

    🎨 FUN SITES (Easy Targets):
    ├─ geocities.com (202.1.1.100)
    │  └─ admin:admin (seriously)
    │  └─ World-writable directories!
    │
    └─ altavista.com (202.3.3.100)
       └─ 90s search engine

    🎓 EDUCATIONAL:
    └─ mit.edu (203.1.1.100)
       └─ AI research papers

    HACKER TOOLS AT YOUR DISPOSAL:
    ✓ ping <domain>     - Test connectivity
    ✓ nmap <domain>     - Scan for open ports
    ✓ ssh <domain>      - Try to login
    ✓ curl <domain>     - View websites
    ✓ nslookup <domain> - DNS lookups

    PROTIP: Check .bash_history and hidden files!
    PROTIP: Look for passwords.txt files!
    PROTIP: /etc/hosts might have interesting entries!

    """)

    print("="*70)
    print("INTERNET IS READY - HAPPY HACKING!")
    print("="*70)

    return network, systems


if __name__ == '__main__':
    network, systems = create_hackable_internet()

    print("\nTesting DNS resolution...")
    laptop = systems['laptop']

    ec, out, err = laptop.execute_command('nslookup megacorp.com')
    if '200.1.1.100' in out:
        print("✓ DNS working!")
    else:
        print("✗ DNS failed")

    print("\nTesting network connectivity...")
    path = network.virtual_network._find_route_path('192.168.1.100', '200.1.1.100')
    if path:
        print(f"✓ Route to megacorp: {' → '.join(path)}")

    print("\n🎮 THE HACKABLE INTERNET IS LIVE! 🎮")
