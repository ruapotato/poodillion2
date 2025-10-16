"""
December 1990 World Builder
Creates an immersive early internet experience with BBS systems,
mysterious networks, and period-appropriate technology.
"""

from core.system import UnixSystem
from core.network import VirtualNetwork


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
    attacker = UnixSystem(
        hostname='kali-box',
        ip='192.168.13.37',
        network=network
    )
    attacker.description = "Your terminal. A mysterious invitation brought you here."
    network.add_system(attacker)

    # Add missions directory
    attacker.vfs.mkdir('/missions', 0o755, 0, 0, 1)

    # ========================================
    # BBS SYSTEMS - The Backbone of 1990
    # ========================================

    # Main BBS Hub
    bbs_main = UnixSystem(
        hostname='bbs.cyberspace.net',
        ip='192.168.1.10',
        network=network
    )
    bbs_main.description = "CyberSpace BBS - The Hub of the Underground"
    network.add_system(bbs_main)

    # Underground BBS
    bbs_underground = UnixSystem(
        hostname='underground.bbs',
        ip='192.168.1.11',
        network=network
    )
    bbs_underground.description = "The Underground - Where Hackers Meet"
    network.add_system(bbs_underground)

    # Corp BBS
    bbs_corp = UnixSystem(
        hostname='megacorp.bbs',
        ip='192.168.2.50',
        network=network
    )
    bbs_corp.description = "MegaCorp Internal BBS"
    network.add_system(bbs_corp)

    # ========================================
    # UNIVERSITY SYSTEMS
    # ========================================

    # University mainframe
    university = UnixSystem(
        hostname='vax.university.edu',
        ip='192.168.3.100',
        network=network
    )
    university.description = "University VAX System - Research Network"
    network.add_system(university)

    # ========================================
    # MYSTERIOUS SYSTEMS
    # ========================================

    # The Nexus - Something alien
    nexus = UnixSystem(
        hostname='nexus.unknown',
        ip='192.168.99.1',
        network=network
    )
    nexus.description = "??? - Origin Unknown"
    network.add_system(nexus)

    # Research facility
    research = UnixSystem(
        hostname='research.facility.gov',
        ip='192.168.4.66',
        network=network
    )
    research.description = "Government Research Facility"
    network.add_system(research)

    # ========================================
    # COMMERCIAL SYSTEMS
    # ========================================

    # CyberMart Shopping Server
    cybermart = UnixSystem(
        hostname='shopserv.cybermart.com',
        ip='192.168.5.100',
        network=network
    )
    cybermart.description = "CyberMart Shopping Server - Online retail"
    network.add_system(cybermart)

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

    # All systems
    all_systems = [
        attacker,
        bbs_main,
        bbs_underground,
        bbs_corp,
        university,
        nexus,
        research,
        cybermart
    ]

    return attacker, network, all_systems


def populate_attacker_system(system):
    """Populate the attacker's starting system"""
    vfs = system.vfs

    # Create mission files
    vfs.create_file('/missions/README', 0o644, 0, 0, b"""
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
""", 1)

    vfs.create_file('/missions/01_first_contact', 0o644, 0, 0, b"""
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
""", 1)

    vfs.create_file('/missions/02_underground', 0o644, 0, 0, b"""
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
""", 1)

    vfs.create_file('/missions/03_corporate_secrets', 0o644, 0, 0, b"""
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
""", 1)

    vfs.create_file('/missions/04_university_access', 0o644, 0, 0, b"""
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
""", 1)

    vfs.create_file('/missions/05_the_nexus', 0o644, 0, 0, b"""
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
""", 1)
    vfs.create_file('/missions/06_credit_heist', 0o644, 0, 0, b"""
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
""", 1)


    # Create home directory files
    vfs.create_file('/root/README', 0o644, 0, 0, b"""You are root on kali-box.

This terminal was provided to you by an anonymous source.
Someone wanted you on this network tonight.

Check /missions/ for objectives.
Use 'lynx' to browse BBS systems.
Use 'nmap' to scan for systems.

Good luck.
""", 1)

    vfs.create_file('/root/.profile', 0o644, 0, 0, b"""# Profile for anonymous user
export PS1="[\\u@\\h \\W]\\$ "
export PATH=/bin:/usr/bin:/sbin:/usr/sbin
export TERM=vt100

# Display hint on login
if [ -f /missions/README ]; then
    echo ""
    echo "Type: cat /missions/README"
    echo ""
fi
""", 1)


def populate_bbs_main(system):
    """Populate the main CyberSpace BBS"""
    vfs = system.vfs

    # Will be populated with BBS content via website files
    # The lynx browser will display these
    pass


def populate_bbs_underground(system):
    """Populate the Underground BBS"""
    vfs = system.vfs

    # Create hidden directory
    vfs.mkdir('/hidden', 0o700, 0, 0, 1)
    vfs.create_file('/hidden/elite.txt', 0o600, 0, 0, b"""
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
""", 1)


def populate_bbs_corp(system):
    """Populate the MegaCorp BBS"""
    vfs = system.vfs

    vfs.mkdir('/corp', 0o755, 0, 0, 1)
    vfs.mkdir('/corp/projects', 0o700, 0, 0, 1)

    vfs.create_file('/corp/projects/PROJECT_NEXUS.txt', 0o600, 0, 0, b"""
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
""", 1)


def populate_university(system):
    """Populate the university VAX system"""
    vfs = system.vfs

    # Create home directories
    vfs.mkdir('/home', 0o755, 0, 0, 1)
    vfs.mkdir('/home/smitchell', 0o755, 1001, 100, 1)
    vfs.mkdir('/home/smitchell/mail', 0o700, 1001, 100, 1)

    vfs.create_file('/home/smitchell/mail/inbox', 0o600, 1001, 100, b"""
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
""", 1)

    vfs.create_file('/home/smitchell/research_notes.txt', 0o644, 1001, 100, b"""
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
""", 1)


def populate_nexus(system):
    """Populate the mysterious Nexus system"""
    vfs = system.vfs

    vfs.create_file('/root/WELCOME', 0o644, 0, 0, b"""
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
""", 1)

    vfs.create_file('/root/MESSAGE', 0o644, 0, 0, b"""
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
""", 1)


def populate_research(system):
    """Populate the government research facility"""
    vfs = system.vfs

    vfs.mkdir('/classified', 0o700, 0, 0, 1)

    vfs.create_file('/classified/NEXUS_REPORT.txt', 0o600, 0, 0, b"""
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
""", 1)

    vfs.create_file('/classified/contact_log.txt', 0o600, 0, 0, b"""
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
""", 1)


# Make the function available
__all__ = ['create_december_1990_world']


def populate_cybermart(system):
    """Populate the CyberMart shopping server"""
    vfs = system.vfs

    # Create shop directories
    vfs.mkdir('/shop', 0o755, 0, 0, 1)
    vfs.mkdir('/shop/customers', 0o755, 0, 0, 1)
    vfs.mkdir('/shop/payments', 0o700, 0, 0, 1)

    # Create customer database with CC numbers (insecure!)
    vfs.create_file('/shop/customers/database.txt', 0o644, 0, 0, b"""CYBERMART CUSTOMER DATABASE
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
""", 1)

    # Create admin note about credentials
    vfs.create_file('/shop/ADMIN_README', 0o644, 0, 0, b"""CYBERMART SHOP SERVER

Server: shopserv.cybermart.com (192.168.5.100)
Admin access: admin / cyber@mart90

WARNING: Change default password!
TODO: Move customer data to encrypted storage!
TODO: Fix file permissions on database!

Customer DB: /shop/customers/database.txt
Payment logs: /shop/payments/

For support contact: admin@cybermart.com
""", 1)

