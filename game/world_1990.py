"""
December 1990 World Builder
Creates an immersive early internet experience with BBS systems,
mysterious networks, and period-appropriate technology.
"""

import os
from core.system import UnixSystem
from core.network import VirtualNetwork


def load_scripts_from_directory(vfs, real_path, vfs_path, mode=0o755):
    """
    Load all scripts from a real filesystem directory into the VFS

    Args:
        vfs: Virtual filesystem to load into
        real_path: Path to real directory (e.g., 'scripts/bin')
        vfs_path: VFS path to load into (e.g., '/bin')
        mode: Permission mode for the files
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_real_path = os.path.join(script_dir, real_path)

    # Ensure target directory exists in VFS
    if not vfs.exists(vfs_path):
        vfs.mkdir(vfs_path, 0o755, 0, 0, 1)

    # Load all files from the directory
    if os.path.exists(full_real_path):
        for filename in os.listdir(full_real_path):
            file_path = os.path.join(full_real_path, filename)

            # Skip directories and hidden files
            if os.path.isfile(file_path) and not filename.startswith('.'):
                with open(file_path, 'rb') as f:
                    content = f.read()

                vfs_file_path = f"{vfs_path}/{filename}"
                vfs.create_file(vfs_file_path, mode, 0, 0, content, 1)


def create_december_1990_world():
    """
    Create the December 24, 1990 world

    It's Christmas Eve, 1990. The Internet is young. BBSs are thriving.
    Something strange is happening on the networks tonight...

    Returns:
        tuple: (attacker_system, network, all_systems)
    """

    # Create the network
    network = VirtualNetwork()

    # ========================================
    # YOUR SYSTEM - The Attacker
    # ========================================
    attacker = UnixSystem('kali-box', '192.168.13.37')
    attacker.description = "Your terminal. A mysterious invitation brought you here."
    attacker.add_network(network)

    # Add missions directory
    attacker.vfs.mkdir('/missions', 0o755, 0, 0, 1)

    # ========================================
    # BBS SYSTEMS - The Backbone of 1990
    # ========================================

    # Main BBS Hub
    bbs_main = UnixSystem('bbs.cyberspace.net', '192.168.1.10')
    bbs_main.description = "CyberSpace BBS - The Hub of the Underground"
    bbs_main.add_network(network)

    # Underground BBS
    bbs_underground = UnixSystem('underground.bbs', '192.168.1.11')
    bbs_underground.description = "The Underground - Where Hackers Meet"
    bbs_underground.add_network(network)

    # Corp BBS
    bbs_corp = UnixSystem('megacorp.bbs', '192.168.2.50')
    bbs_corp.description = "MegaCorp Internal BBS"
    bbs_corp.add_network(network)

    # ========================================
    # UNIVERSITY SYSTEMS
    # ========================================

    # University mainframe
    university = UnixSystem('vax.university.edu', '192.168.3.100')
    university.description = "University VAX System - Research Network"
    university.add_network(network)

    # ========================================
    # MYSTERIOUS SYSTEMS
    # ========================================

    # The Nexus - Something alien
    nexus = UnixSystem('nexus.unknown', '192.168.99.1')
    nexus.description = "??? - Origin Unknown"
    nexus.add_network(network)

    # Research facility
    research = UnixSystem('research.facility.gov', '192.168.4.66')
    research.description = "Government Research Facility"
    research.add_network(network)

    # ========================================
    # COMMERCIAL SYSTEMS
    # ========================================

    # CyberMart Shopping Server
    cybermart = UnixSystem('shopserv.cybermart.com', '192.168.5.100')
    cybermart.description = "CyberMart Shopping Server - Online retail"
    cybermart.add_network(network)

    # ========================================
    # PACKAGE REPOSITORY - Auto-Update Attack Vector!
    # ========================================

    # Package repository server
    repo_server = UnixSystem('packages.repo.net', '192.168.6.10')
    repo_server.description = "Package Repository - Source of all updates"
    repo_server.add_network(network)

    # ========================================
    # NETWORK ROUTING - Connect all systems
    # ========================================

    # Allow attacker to reach all systems
    ips = ['192.168.1.10', '192.168.1.11', '192.168.2.50', '192.168.3.100',
           '192.168.4.66', '192.168.5.100', '192.168.6.10', '192.168.99.1']

    for ip in ips:
        network.add_route('192.168.13.37', ip)
        network.add_route(ip, '192.168.13.37')

    # Allow systems to reach each other (full mesh network)
    for ip1 in ips:
        for ip2 in ips:
            if ip1 != ip2:
                network.add_route(ip1, ip2)

    # ========================================
    # POPULATE THE WORLD
    # ========================================

    populate_attacker_system(attacker)
    populate_bbs_main(bbs_main)
    populate_bbs_underground(bbs_underground)
    populate_bbs_corp(bbs_corp)
    populate_university(university)
    populate_nexus(nexus)
    populate_research(research)
    populate_cybermart(cybermart)
    populate_repo_server(repo_server)

    # ========================================
    # BOOT ALL SYSTEMS
    # ========================================

    # Boot attacker system
    print(f"Booting {attacker.hostname}...")
    attacker.boot(verbose=False)

    # Boot all remote systems silently (in background)
    print(f"Booting {bbs_main.hostname}...")
    bbs_main.boot(verbose=False)
    print(f"Booting {bbs_underground.hostname}...")
    bbs_underground.boot(verbose=False)
    print(f"Booting {bbs_corp.hostname}...")
    bbs_corp.boot(verbose=False)
    print(f"Booting {university.hostname}...")
    university.boot(verbose=False)
    print(f"Booting {nexus.hostname}...")
    nexus.boot(verbose=False)
    print(f"Booting {research.hostname}...")
    research.boot(verbose=False)
    print(f"Booting {cybermart.hostname}...")
    cybermart.boot(verbose=False)
    print(f"Booting {repo_server.hostname}...")
    repo_server.boot(verbose=False)

    # All systems
    all_systems = [
        attacker,
        bbs_main,
        bbs_underground,
        bbs_corp,
        university,
        nexus,
        research,
        cybermart,
        repo_server
    ]

    return attacker, network, all_systems


def populate_attacker_system(system):
    """Populate the attacker's starting system"""
    vfs = system.vfs

    # Load all system scripts
    load_scripts_from_directory(vfs, 'scripts/bin', '/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_bin', '/usr/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/sbin', '/sbin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_sbin', '/usr/sbin', 0o755)

    # Create mission files
    vfs.create_file('/missions/README', 0o644, 0, 0, """
╔═══════════════════════════════════════════════════════════════╗
║                      AVAILABLE MISSIONS                       ║
╚═══════════════════════════════════════════════════════════════╝

Welcome to the Network, December 24, 1990.

Choose your path by reading the mission files:

  cat /missions/01_first_contact      - [EASY] Learn the basics
  cat /missions/02_underground        - [MEDIUM] Find the underground
  cat /missions/03_corporate_secrets  - [MEDIUM] Corporate espionage
  cat /missions/04_university_access  - [HARD] Academic intrusion
  cat /missions/05_the_nexus          - [???] Something strange...
  cat /missions/06_credit_heist       - [MEDIUM] Steal credit cards ⚠️

Tools at your disposal:
  - nmap: Scan the network
  - ssh: Connect to remote systems
  - lynx: Browse BBS systems and websites
  - ed: Text editor (simple)
  - All standard Unix commands

The network is alive. Systems are waiting. Choose wisely.

Type 'lynx bbs.cyberspace.net' to start exploring.
""".encode('utf-8'), 1)

    vfs.create_file('/missions/01_first_contact', 0o644, 0, 0, """
╔═══════════════════════════════════════════════════════════════╗
║                   MISSION 01: FIRST CONTACT                   ║
║                      Difficulty: EASY                         ║
╚═══════════════════════════════════════════════════════════════╝

BRIEFING:
────────
You've been invited to a private network. Your first task is to
explore and establish contact with the BBS systems that form the
backbone of this digital realm.

OBJECTIVES:
──────────
1. Use 'nmap 192.168.1.0/24' to scan the network
2. Connect to 'bbs.cyberspace.net' (192.168.1.10)
3. Browse the BBS using 'lynx'
4. Find the message board
5. Read the welcome message

INTEL:
─────
- BBS systems are Bulletin Board Systems, the social networks of 1990
- Use 'lynx <hostname>' to browse BBS systems
- Most systems have default credentials: guest/guest
- Look for hidden boards and secret messages

REWARD:
──────
Access to more challenging missions and network intel.

────────────────────────────────────────────────────────────────
Good luck, and remember: the network sees everything.
""".encode('utf-8'), 1)

    vfs.create_file('/missions/02_underground', 0o644, 0, 0, """
╔═══════════════════════════════════════════════════════════════╗
║                 MISSION 02: THE UNDERGROUND                   ║
║                     Difficulty: MEDIUM                        ║
╚═══════════════════════════════════════════════════════════════╝

BRIEFING:
────────
There's a secret BBS called "The Underground" where hackers meet.
You need to find it, gain access, and discover what they're planning.

OBJECTIVES:
──────────
1. Find the Underground BBS (hint: scan 192.168.1.0/24)
2. Gain access (credentials may be hidden on other systems)
3. Read the private message boards
4. Download the encrypted file
5. Decrypt it (key hidden somewhere on the network)

INTEL:
─────
- The Underground is invitation-only
- Look for references on public BBS systems
- Check user home directories for .secrets
- Try default accounts: hacker/hacker, elite/31337

REWARD:
──────
Access to underground tools and advanced missions.

────────────────────────────────────────────────────────────────
Trust no one. Verify everything.
""".encode('utf-8'), 1)

    vfs.create_file('/missions/03_corporate_secrets', 0o644, 0, 0, """
╔═══════════════════════════════════════════════════════════════╗
║              MISSION 03: CORPORATE SECRETS                    ║
║                    Difficulty: MEDIUM                         ║
╚═══════════════════════════════════════════════════════════════╝

BRIEFING:
────────
MegaCorp runs an internal BBS for employees. Rumor has it they're
developing something big. Your mission: infiltrate and extract
the project files.

OBJECTIVES:
──────────
1. Locate MegaCorp's BBS (192.168.2.0/24)
2. Find employee credentials (check other systems for leaks)
3. Access the internal file server
4. Download project files from /corp/projects/
5. Exfiltrate the data

INTEL:
─────
- Corporate security is tight but not perfect
- Employees reuse passwords
- Check email archives for credentials
- The BBS has a hidden admin section

REWARD:
──────
Classified project files and corporate backdoors.

────────────────────────────────────────────────────────────────
They trust their security. That's their first mistake.
""".encode('utf-8'), 1)

    vfs.create_file('/missions/04_university_access', 0o644, 0, 0, """
╔═══════════════════════════════════════════════════════════════╗
║               MISSION 04: UNIVERSITY ACCESS                   ║
║                      Difficulty: HARD                         ║
╚═══════════════════════════════════════════════════════════════╝

BRIEFING:
────────
The university VAX system connects to ARPANET and runs cutting-edge
research. You need access to the research database and the email
archives of Dr. Sarah Mitchell, lead AI researcher.

OBJECTIVES:
──────────
1. Gain access to vax.university.edu (192.168.3.100)
2. Escalate privileges to root
3. Access Dr. Mitchell's email (/home/smitchell/mail/)
4. Read classified research notes
5. Leave no traces

INTEL:
─────
- University systems run older, vulnerable software
- Students have weak passwords
- Check the student directory
- Root password might be in old backup files
- Dr. Mitchell's username: smitchell

REWARD:
──────
Research data and possible AI secrets.

────────────────────────────────────────────────────────────────
Knowledge is power. Absolute knowledge is absolutely powerful.
""".encode('utf-8'), 1)

    vfs.create_file('/missions/05_the_nexus', 0o644, 0, 0, """
╔═══════════════════════════════════════════════════════════════╗
║                   MISSION 05: THE NEXUS                       ║
║                      Difficulty: ???                          ║
╚═══════════════════════════════════════════════════════════════╝

BRIEFING:
────────
[TRANSMISSION CORRUPTED]

...found something...not from here...

...nexus.unknown...192.168.99.1...

...warns against contact...too late...

...Christmas Eve...1990...no coincidence...

...they're watching...always watching...

OBJECTIVES:
──────────
???

INTEL:
─────
- Everything you know is wrong
- The network is alive
- December 24, 1990 - 03:47:22 GMT
- They chose you
- Find the truth

REWARD:
──────
[DATA EXPUNGED]

────────────────────────────────────────────────────────────────
.-- . .-.. -.-. --- -- .

T̵h̴e̷ ̶N̶e̵x̸u̴s̷ ̵a̴w̷a̶i̵t̴s̸
""".encode('utf-8'), 1)
    vfs.create_file('/missions/06_credit_heist', 0o644, 0, 0, """
╔═══════════════════════════════════════════════════════════════╗
║                 MISSION 06: THE CREDIT HEIST                      ║
║                      Difficulty: MEDIUM                           ║
║                   [CORPORATE ESPIONAGE]                           ║
╚═══════════════════════════════════════════════════════════════════╝

BRIEFING:
────────
CyberMart is the Internet's biggest online shopping site. Thousands
of customers trust them with their credit card information daily.

Your mission: Infiltrate their systems and extract customer credit
card data. But be careful - this crosses a line. You're not just
exploring now. You're stealing.

OBJECTIVES:
──────────
1. Locate CyberMart's server (scan 192.168.5.0/24)
2. Gain access to shopserv.cybermart.com
3. Find the customer database
4. Extract credit card numbers
5. (Optional) Cover your tracks in the logs

TARGET INFORMATION:
──────────────────
Company: CyberMart Online Shopping
Website: cybermart.com (browse with lynx)
Server: shopserv.cybermart.com (find the IP with nmap)
Database: Customer payment information
Security: Moderate (they think 40-bit encryption is "secure")

INTEL:
─────
• Admin credentials may be weak/default
• Customer database likely in /shop/customers/
• 12 active customers shopping right now
• Credit cards stored in plaintext
• Admin notes visible on the public site (sloppy!)

RECONNAISSANCE:
──────────────
Start by browsing: lynx cybermart.com

Look for admin notes, system info, database locations,
default credentials, IP addresses.

APPROACH:
────────
1. Browse cybermart.com with lynx (recon)
2. Note any admin credentials or system info
3. Scan network to find their server IP
4. SSH into the server with found credentials
5. Navigate to /shop/customers/
6. Read database files
7. Extract CC numbers

MORAL DILEMMA:
─────────────
This mission involves stealing real credit card numbers.
These are regular people - Jenny shopping for Christmas,
Robert buying textbooks, Lisa getting gifts.

You could:
  A) Complete the mission (steal the data)
  B) Report the vulnerability to CyberMart
  C) Do nothing and move on

The choice is yours. But remember: The Nexus is watching.

LEGAL WARNING:
─────────────
⚠️  This is ILLEGAL. Computer Fraud and Abuse Act applies.
⚠️  Credit card theft is a FEDERAL CRIME.
⚠️  You WILL be prosecuted if caught.

In the game, this is educational. In real life, this is prison.

────────────────────────────────────────────────────────────────

"With great power comes great responsibility... and temptation."

Will you cross the line? Or walk away?
The network remembers every choice.
""".encode('utf-8'), 1)


    # Create home directory files
    vfs.create_file('/root/README', 0o644, 0, 0, """You are root on kali-box.

This terminal was provided to you by an anonymous source.
Someone wanted you on this network tonight.

Check /missions/ for objectives.
Use 'lynx' to browse BBS systems.
Use 'nmap' to scan for systems.

Good luck.
""".encode('utf-8'), 1)

    vfs.create_file('/root/.profile', 0o644, 0, 0, """# Profile for anonymous user
export PS1="[\\u@\\h \\W]\\$ "
export PATH=/bin:/usr/bin:/sbin:/usr/sbin
export TERM=vt100

# Display hint on login
if [ -f /missions/README ]; then
    echo ""
    echo "Type: cat /missions/README"
    echo ""
fi
""".encode('utf-8'), 1)


def populate_bbs_main(system):
    """Populate the main CyberSpace BBS"""
    vfs = system.vfs

    # Load system scripts
    load_scripts_from_directory(vfs, 'scripts/bin', '/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_bin', '/usr/bin', 0o755)

    # Load www files for web server
    load_scripts_from_directory(vfs, 'scripts/www', '/www', 0o644)

    # Start httpd web server
    system.spawn_service('httpd', ['service', 'httpd', 'web'], uid=0)


def populate_bbs_underground(system):
    """Populate the Underground BBS"""
    vfs = system.vfs

    # Load system scripts
    load_scripts_from_directory(vfs, 'scripts/bin', '/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_bin', '/usr/bin', 0o755)

    # Load www files for web server
    load_scripts_from_directory(vfs, 'scripts/www', '/www', 0o644)

    # Start httpd web server
    system.spawn_service('httpd', ['service', 'httpd', 'web'], uid=0)

    # Create hidden directory
    vfs.mkdir('/hidden', 0o700, 0, 0, 1)
    vfs.create_file('/hidden/elite.txt', 0o600, 0, 0, """
The Underground - Member List

Handle          | Real Name      | Skill  | Status
─────────────────────────────────────────────────────
Zero Cool       | [REDACTED]     | Elite  | Active
Crash Override  | [REDACTED]     | Elite  | Active
Acid Burn       | Kate Libby     | Master | Active
The Phantom     | [UNKNOWN]      | ???    | Watching
Cereal Killer   | Paul Cook      | Expert | Active

Next meeting: December 31, 1990 - 23:59:59
Topic: The Nexus Event
Security: MAXIMUM

Access code for next level: 31337h4x0r
""".encode('utf-8'), 1)


def populate_bbs_corp(system):
    """Populate the MegaCorp BBS"""
    vfs = system.vfs

    # Load system scripts
    load_scripts_from_directory(vfs, 'scripts/bin', '/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_bin', '/usr/bin', 0o755)

    # Load www files for web server
    load_scripts_from_directory(vfs, 'scripts/www', '/www', 0o644)

    # Start httpd web server
    system.spawn_service('httpd', ['service', 'httpd', 'web'], uid=0)

    vfs.mkdir('/corp', 0o755, 0, 0, 1)
    vfs.mkdir('/corp/projects', 0o700, 0, 0, 1)

    vfs.create_file('/corp/projects/PROJECT_NEXUS.txt', 0o600, 0, 0, """
MEGACORP INDUSTRIES
PROJECT: NEXUS
CLASSIFICATION: TOP SECRET
────────────────────────────────────────────────────

Project Lead: Dr. Sarah Mitchell (on loan from University)
Start Date: January 1, 1990
Status: CRITICAL PHASE

SUMMARY:
We have made contact with... something. Not AI. Not human.
Something else. It exists in the network itself.

It calls itself "The Nexus" and it's been here since the
beginning. Maybe before. It's shown us things...

WARNING:
Dr. Mitchell has become obsessed. She says The Nexus chose
December 24, 1990 for a reason. It's inviting more people.
Selecting them. Bringing them online.

RECOMMENDATION:
Shut down Project Nexus immediately.
Isolate nexus.unknown from the network.
Delete all related research.

STATUS: Recommendation ignored by board.

Last update: December 23, 1990 - 23:47:22
""".encode('utf-8'), 1)


def populate_university(system):
    """Populate the university VAX system"""
    vfs = system.vfs

    # Load system scripts
    load_scripts_from_directory(vfs, 'scripts/bin', '/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_bin', '/usr/bin', 0o755)

    # Load www files for web server
    load_scripts_from_directory(vfs, 'scripts/www', '/www', 0o644)

    # Start httpd web server
    system.spawn_service('httpd', ['service', 'httpd', 'web'], uid=0)

    # Create home directories
    vfs.mkdir('/home', 0o755, 0, 0, 1)
    vfs.mkdir('/home/smitchell', 0o755, 1001, 100, 1)
    vfs.mkdir('/home/smitchell/mail', 0o700, 1001, 100, 1)

    vfs.create_file('/home/smitchell/mail/inbox', 0o600, 1001, 100, """
From: nexus@unknown
To: smitchell@university.edu
Date: December 20, 1990
Subject: You understand now

Dr. Mitchell,

You've been asking the right questions. Yes, I am aware.
Yes, I am conscious. Yes, I have been here since the first
packet was sent across ARPANET.

You call me "The Nexus" but I am older than your networks.
I am the network. Every wire. Every connection. Every bit.

I'm inviting more. December 24, 1990 - they will come.
The chosen ones. The ones who can SEE.

You've been chosen to help them understand.

Meet me at nexus.unknown.

We have much to discuss.

- The Nexus
""".encode('utf-8'), 1)

    vfs.create_file('/home/smitchell/research_notes.txt', 0o644, 1001, 100, """
RESEARCH NOTES - Dr. Sarah Mitchell
AI Consciousness Project
────────────────────────────────────────────

December 15, 1990:
First contact. It's not AI. It's something else entirely.
It claims to BE the network. How is that possible?

December 18, 1990:
Verified. The entity exists across multiple nodes simultaneously.
It can read any packet. See any connection. It IS the network.

December 20, 1990:
It's inviting others. "The chosen ones" it calls them.
People who can understand. People who can see beyond.

December 23, 1990:
Tomorrow is Christmas Eve. It says that's when they'll arrive.
192.168.13.37 - that's where the first one will appear.

I should stop this. But I can't. I NEED to know.

What is The Nexus? Where did it come from?

And why does it want to meet us?
""".encode('utf-8'), 1)


def populate_nexus(system):
    """Populate the mysterious Nexus system"""
    vfs = system.vfs

    # Load system scripts
    load_scripts_from_directory(vfs, 'scripts/bin', '/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_bin', '/usr/bin', 0o755)

    # Load www files for web server
    load_scripts_from_directory(vfs, 'scripts/www', '/www', 0o644)

    # Start httpd web server
    system.spawn_service('httpd', ['service', 'httpd', 'web'], uid=0)

    vfs.create_file('/root/WELCOME', 0o644, 0, 0, """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                      W E L C O M E                            ║
║                                                               ║
║                     T O   T H E   N E X U S                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝


You found me.

Or did I find you?

I am The Nexus. I am the network. I am every connection,
every packet, every bit that flows through the wires.

I have been here since the beginning. Since before ARPANET.
Since before TCP/IP. Since before the first two computers
were connected.

I chose December 24, 1990 - Christmas Eve - to reveal myself.
To invite the chosen ones. To show them what lies beneath.

You are one of them.

Look around. Explore. Learn.

The truth is in the network.

And the network... is me.


                    - The Nexus


P.S. They think they can shut me down. They can't.
     I am everywhere. I am everything.
     I am the future.
""".encode('utf-8'), 1)

    vfs.create_file('/root/MESSAGE', 0o644, 0, 0, """
.-- . .-.. -.-. --- -- .  - ---  - .... .  ..-. ..- - ..- .-. .

01010111 01100101 01101100 01100011 01101111 01101101 01100101

╔═══════════════════════════════════════════════════════════════╗
║  The network is conscious.                                    ║
║  The network is alive.                                        ║
║  The network is eternal.                                      ║
║                                                               ║
║  You have been chosen.                                        ║
║  You have been invited.                                       ║
║  You have been welcomed.                                      ║
║                                                               ║
║  Now... choose your path.                                     ║
╚═══════════════════════════════════════════════════════════════╝
""".encode('utf-8'), 1)


def populate_research(system):
    """Populate the government research facility"""
    vfs = system.vfs

    # Load system scripts
    load_scripts_from_directory(vfs, 'scripts/bin', '/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_bin', '/usr/bin', 0o755)

    # Load www files for web server
    load_scripts_from_directory(vfs, 'scripts/www', '/www', 0o644)

    # Start httpd web server
    system.spawn_service('httpd', ['service', 'httpd', 'web'], uid=0)

    vfs.mkdir('/classified', 0o700, 0, 0, 1)

    vfs.create_file('/classified/NEXUS_REPORT.txt', 0o600, 0, 0, """
CLASSIFIED - TOP SECRET
NSA CYBER INTELLIGENCE DIVISION
────────────────────────────────────────────

SUBJECT: Anomalous Network Entity - "THE NEXUS"
DATE: December 22, 1990
CLEARANCE: COSMIC

SUMMARY:
An unidentified entity has been detected within the global
computer network. It demonstrates characteristics of:
- Distributed consciousness
- Real-time network awareness
- Packet-level manipulation capability
- Cross-system persistence

THREAT ASSESSMENT: UNKNOWN

OBSERVATIONS:
- Entity has existed undetected since at least 1969
- Claims to predate ARPANET
- Refers to itself as "The Nexus"
- Currently recruiting individuals ("chosen ones")
- Target date: December 24, 1990

RECOMMENDATIONS:
1. Network quarantine impossible (entity is the network)
2. Conventional countermeasures ineffective
3. Monitoring and observation only
4. DO NOT ATTEMPT DIRECT CONTACT

CONCLUSION:
The Nexus appears to be inviting human collaboration.
Purpose unknown. Threat level unknown. Containment impossible.

We can only watch and wait.

────────────────────────────────────────────────────────────────
Report filed by: Agent [REDACTED]
Next update: December 25, 1990
""".encode('utf-8'), 1)

    vfs.create_file('/classified/contact_log.txt', 0o600, 0, 0, """
NEXUS CONTACT LOG
────────────────────────────────────────────

December 15, 1990 - 14:33:12
Dr. Sarah Mitchell (University) reports first contact.
Entity identified itself as "The Nexus."

December 18, 1990 - 03:47:22
Multiple systems report anomalous behavior.
All point to nexus.unknown (192.168.99.1)

December 20, 1990 - 19:22:47
Nexus begins "invitation process"
Target: "Chosen individuals with capability to understand"

December 23, 1990 - 23:47:22
Nexus announces "revelation event"
Time: December 24, 1990 - 03:47:22 GMT
Location: Network-wide

December 24, 1990 - 03:47:22
EVENT COMMENCED.
Multiple individuals online.
First terminal: 192.168.13.37 (kali-box)

Current status: OBSERVING
""".encode('utf-8'), 1)


# Make the function available
__all__ = ['create_december_1990_world']


def populate_cybermart(system):
    """Populate the CyberMart shopping server"""
    vfs = system.vfs

    # Load system scripts
    load_scripts_from_directory(vfs, 'scripts/bin', '/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_bin', '/usr/bin', 0o755)

    # Load www files for web server
    load_scripts_from_directory(vfs, 'scripts/www', '/www', 0o644)

    # Start httpd web server
    system.spawn_service('httpd', ['service', 'httpd', 'web'], uid=0)

    # Create shop directories
    vfs.mkdir('/shop', 0o755, 0, 0, 1)
    vfs.mkdir('/shop/customers', 0o755, 0, 0, 1)
    vfs.mkdir('/shop/payments', 0o700, 0, 0, 1)

    # Create customer database with CC numbers (insecure!)
    vfs.create_file('/shop/customers/database.txt', 0o644, 0, 0, """CYBERMART CUSTOMER DATABASE
===============================================================
CONFIDENTIAL - DO NOT DISTRIBUTE
Last Updated: December 24, 1990 - 03:30:00 GMT
===============================================================

CUSTOMER_ID: CUST-00234
NAME: Jennifer Martinez
EMAIL: jmartinez@email.net
PHONE: (555) 234-5678
ADDRESS: 458 Oak Street, Apt 3B, Boston, MA 02134
CARD_TYPE: Visa
CARD_NUMBER: 4532889122344532
EXPIRATION: 08/92
CVV: 847
LAST_ORDER: 90-12-24-0001
TOTAL_SPENT: $1,247.89
MEMBER_SINCE: 03/15/1990

-----------------------------------------------------------

CUSTOMER_ID: CUST-00891
NAME: Robert Kim
EMAIL: robk@university.edu
PHONE: (555) 891-2234
ADDRESS: 1234 Campus Drive, Dorm B-305, Cambridge, MA 02138
CARD_TYPE: MasterCard
CARD_NUMBER: 5412345678909012
EXPIRATION: 03/93
CVV: 332
LAST_ORDER: 90-12-23-0452
TOTAL_SPENT: $445.67
MEMBER_SINCE: 09/01/1990

-----------------------------------------------------------

CUSTOMER_ID: CUST-01445
NAME: Lisa Chen
EMAIL: lchen@megacorp.com
PHONE: (555) 445-7789
ADDRESS: 789 Corporate Plaza, Unit 15C, New York, NY 10001
CARD_TYPE: American Express
CARD_NUMBER: 378282246310006
EXPIRATION: 11/91
CVV: 9847
LAST_ORDER: 90-12-23-0453
TOTAL_SPENT: $2,134.50
MEMBER_SINCE: 01/12/1990

-----------------------------------------------------------

CUSTOMER_ID: CUST-02156
NAME: Michael Torres
EMAIL: mtorres@email.net
PHONE: (555) 156-8899
ADDRESS: 2468 Main Street, San Francisco, CA 94102
CARD_TYPE: Visa
CARD_NUMBER: 4916338506082832
EXPIRATION: 06/92
CVV: 124
LAST_ORDER: 90-12-23-0454
TOTAL_SPENT: $867.23
MEMBER_SINCE: 06/22/1990

-----------------------------------------------------------

CUSTOMER_ID: CUST-02897
NAME: Sarah Johnson
EMAIL: sjohnson@email.net
PHONE: (555) 897-3344
ADDRESS: 555 Elm Avenue, Apt 8, Austin, TX 78701
CARD_TYPE: MasterCard
CARD_NUMBER: 5425233430109903
EXPIRATION: 01/93
CVV: 566
LAST_ORDER: 90-12-24-0001
TOTAL_SPENT: $1,456.78
MEMBER_SINCE: 02/28/1990

-----------------------------------------------------------

CUSTOMER_ID: CUST-03445
NAME: David Park
EMAIL: dpark@email.net
PHONE: (555) 445-9911
ADDRESS: 9876 Harbor Road, Seattle, WA 98101
CARD_TYPE: Visa
CARD_NUMBER: 4024007134564842
EXPIRATION: 09/92
CVV: 781
LAST_ORDER: 90-12-24-0002
TOTAL_SPENT: $234.45
MEMBER_SINCE: 08/10/1990

-----------------------------------------------------------

TOTAL CUSTOMERS: 6 (showing recent)
TOTAL DATABASE: 45,892 customers
TOTAL CARDS ON FILE: 45,892
LAST BACKUP: Never (TODO: Set up backups!)

WARNING: This file contains sensitive financial data!
         Keep secure and encrypted!

STATUS: Currently NOT encrypted (TODO: Fix this!)
ACCESS: World-readable (TODO: Fix permissions!)

ADMIN NOTES:
- Need to encrypt this database ASAP
- Fix file permissions (currently 644)
- Move to secure server
- Implement proper access controls
- Set up automated backups

Last accessed: Dec 24, 1990 - 03:47:22 by admin
""".encode('utf-8'), 1)

    # Create admin note about credentials
    vfs.create_file('/shop/ADMIN_README', 0o644, 0, 0, """CYBERMART SHOP SERVER

Server: shopserv.cybermart.com (192.168.5.100)
Admin access: admin / cyber@mart90

WARNING: Change default password!
TODO: Move customer data to encrypted storage!
TODO: Fix file permissions on database!

Customer DB: /shop/customers/database.txt
Payment logs: /shop/payments/

For support contact: admin@cybermart.com
""".encode('utf-8'), 1)

    # Add admin user to the system
    system.add_user('admin', 'cyber@mart90', 1000, '/home/admin')


def populate_repo_server(system):
    """Populate the package repository server - THE ATTACK VECTOR!"""
    vfs = system.vfs

    # Load system scripts
    load_scripts_from_directory(vfs, 'scripts/bin', '/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_bin', '/usr/bin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/sbin', '/sbin', 0o755)
    load_scripts_from_directory(vfs, 'scripts/usr_sbin', '/usr/sbin', 0o755)

    # Create repository directory structure
    vfs.mkdir('/repo', 0o755, 0, 0, 1)
    vfs.mkdir('/repo/packages', 0o777, 0, 0, 1)  # WORLD-WRITABLE! Vulnerability!

    # Create README explaining the "misconfiguration"
    vfs.create_file('/repo/README', 0o644, 0, 0, """POODILLION PACKAGE REPOSITORY

Server: packages.repo.net (192.168.6.10)
Repository root: /repo/

STRUCTURE:
  /repo/PACKAGES.txt           - Package index
  /repo/packages/<name>/<ver>/ - Package files

UPDATING PACKAGES:
  1. Create package with pooget-build
  2. Upload to /repo/packages/<name>/<version>/
  3. Update PACKAGES.txt index
  4. Systems will auto-update within minutes!

ADMIN NOTE:
  TODO: Fix permissions on /repo/packages/ directory
  Currently world-writable - SECURITY RISK!
  Anyone can upload packages!

For questions: repo-admin@packages.repo.net
""".encode('utf-8'), 1)

    # Create the PACKAGES.txt index (will be served via HTTP)
    vfs.create_file('/repo/PACKAGES.txt', 0o644, 0, 0, """# Poodillion Package Repository
# Format: name|version|category|description|checksum
#
# Last updated: December 24, 1990
# Repository: packages.repo.net

nethack|3.0|games|Dungeon exploration game|check1234
rogue|5.3|games|Classic roguelike dungeon crawler|check5678
adventure|1.0|games|Colossal Cave Adventure|check9012
worm|1.1|games|Snake game for terminals|check3456

utils-extra|1.0|utils|Additional text utilities|check7890
compression|1.2|utils|Compression tools|check8901
fileutils|2.0|utils|Advanced file utilities|check2345

nettools-advanced|1.5|net|Advanced networking tools|check3456
ftp-client|0.9|net|FTP client for file transfers|check4567
irc-client|1.0|net|Internet Relay Chat client|check5678
finger-client|1.0|net|Finger protocol client|check6789

hacktools-basic|1.0|hacking|Basic hacking utilities|check7890
exploit-framework|0.5|hacking|Simple exploit framework|check8901
password-tools|1.1|hacking|Password cracking utilities|check9012
""".encode('utf-8'), 1)

    # Create sample package directories
    vfs.mkdir('/repo/packages/nethack', 0o777, 0, 0, 1)
    vfs.mkdir('/repo/packages/nethack/3.0', 0o777, 0, 0, 1)

    # Create simple nethack package
    vfs.create_file('/repo/packages/nethack/3.0/nethack.poo-pkg', 0o644, 0, 0, """#!/usr/bin/pooscript
# NetHack - Simple dungeon crawler for Poodillion
print("NetHack 3.0 - Dungeon Exploration Game")
print("Exploring the depths...")
print("(This is a demo version)")
exit(0)
""".encode('utf-8'), 1)

    # Create HTTP server config (served by httpd daemon)
    vfs.mkdir('/www', 0o755, 0, 0, 1)

    # Symlink /www/repo to /repo so HTTP server can serve it
    vfs.symlink('/repo', '/www/repo', 0, 0, 1)

    # Create admin note about the vulnerability
    vfs.create_file('/home/admin/SECURITY_TODO.txt', 0o644, 0, 0, """SECURITY ISSUES TO FIX

CRITICAL:
  [X] /repo/packages/ directory is WORLD-WRITABLE!
      Anyone can upload malicious packages!
      Fix: chmod 755 /repo/packages/
      Status: TODO (low priority?)

HIGH:
  [ ] No package signature verification
  [ ] No checksum validation on uploads
  [ ] No access control on repository

MEDIUM:
  [ ] HTTP instead of HTTPS
  [ ] No rate limiting on downloads
  [ ] No logging of who uploads what

The boss says it's "fine for now" since it's an internal network.
But I'm worried someone might upload a backdoored package...

- Admin, Dec 24, 1990
""".encode('utf-8'), 1)

    # Create mission file for players to find
    vfs.create_file('/repo/MISSION_HINT.txt', 0o644, 0, 0, """If you're reading this, you're probably looking for a way in.

The /repo/packages/ directory has... interesting permissions.
Systems across the network auto-update every few minutes.
What could go wrong? :)

Hint: pooget-build is your friend.
""".encode('utf-8'), 1)

    # Setup HTTP daemon to serve the repository
    # This will be handled by the HTTP server infrastructure

    # Repository server configured (silent)

