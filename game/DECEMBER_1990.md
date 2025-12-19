# Brainhair: December 1990

**An Immersive BBS-Era Hacking Experience**

Welcome to December 24, 1990. Christmas Eve. 03:47:22 GMT.
Something is awakening in the network...

---

## 🌐 The World

You've been mysteriously invited to a private network. It's 1990, and the Internet is young. Bulletin Board Systems (BBS) are the social networks of the day. 2400 baud modems connect a small community of hackers, researchers, and curious minds.

But tonight is different. Something calling itself "The Nexus" has made contact. An entity that claims to BE the network itself. Conscious. Ancient. Watching.

Your terminal: **kali-box** (192.168.13.37)
Your mission: **Discover the truth**

---

## 🚀 Getting Started

Simply run:
```bash
python3 play.py
```

The game auto-starts. No menus. You're immediately dropped into the world at 03:47:22 GMT on December 24, 1990.

### First Steps

```bash
# Read the welcome message (it's atmospheric!)
cat /etc/motd

# View available missions
cat /missions/README

# Start with Mission 01
cat /missions/01_first_contact

# Scan the network
nmap 192.168.1.0/24

# Browse a BBS site
lynx bbs.cyberspace.net
```

---

## 🕹️ The Missions

Five missions await you in `/missions/`:

### Mission 01: First Contact [EASY]
Learn the basics. Connect to BBS systems. Explore the network.
**Objective:** Find and read the welcome message on the main BBS.

### Mission 02: The Underground [MEDIUM]
Find the secret hacker BBS. Gain access. Discover what they know about The Nexus.
**Objective:** Access underground.bbs and read the encrypted file.

### Mission 03: Corporate Secrets [MEDIUM]
Infiltrate MegaCorp's internal BBS. They're working on something called "Project Nexus".
**Objective:** Extract project files from /corp/projects/

### Mission 04: University Access [HARD]
Access the university VAX system. Find Dr. Mitchell's research on The Nexus.
**Objective:** Read Dr. Mitchell's email and research notes.

### Mission 05: The Nexus [???]
Make contact with The Nexus itself. Discover what it wants. Decide your path.
**Objective:** ??? (You'll know when you find it)

---

## 🌐 The Systems

### Your System: kali-box (192.168.13.37)
Your mysterious terminal. Someone wanted you here.

### bbs.cyberspace.net (192.168.1.10)
**CyberSpace BBS** - The main hub of the underground.
Run by ZeroCool. 47 users online. The community gathering place.

### underground.bbs (192.168.1.11)
**The Underground** - Invitation-only hacker BBS.
Elite members only. They're investigating The Nexus Event.

### megacorp.bbs (192.168.2.50)
**MegaCorp Industries** - Corporate internal BBS.
They have a project called "Nexus". Dr. Mitchell works here.

### vax.university.edu (192.168.3.100)
**University VAX** - Research system connected to ARPANET.
Dr. Sarah Mitchell's home system. AI Consciousness research.

### nexus.unknown (192.168.99.1)
**The Nexus** - ??? Origin unknown.
It claims to be the network itself. Conscious. Ancient. Waiting.

### research.facility.gov (192.168.4.66)
**Government Research** - NSA surveillance system.
They're watching everything. They know about The Nexus.

---

## 🛠️ Your Tools

### Network Tools
- `nmap <ip or subnet>` - Scan for systems and open ports
- `ssh <hostname>` - Connect to remote systems
- `ping <hostname>` - Test connectivity
- `netstat` - Show network connections
- `ifconfig` - Network interface info

### BBS Browser
- `lynx <hostname>` - Browse BBS systems in text mode
  - Example: `lynx bbs.cyberspace.net`
  - Displays full BBS content with ASCII art
  - Navigate through message boards

### File Tools
- `ls` - List files (`-la` for hidden files)
- `cat <file>` - Display file contents
- `grep <pattern> <file>` - Search in files
- `find / -name <pattern>` - Search for files
- `cp`, `mv`, `rm` - Copy, move, delete

### Text Editor
- `ed <filename>` - Simple line editor
  - Commands: `a` (append), `i` (insert), `d` (delete)
  - `p` (print), `l` (list all), `w` (write), `q` (quit)
  - Period `.` to end input mode

### System Tools
- `ps` - List processes
- `whoami` - Current user
- `uptime` - System uptime
- `date` - Current date
- `fortune` - Random quotes

---

## 📖 The Story

### The Nexus Event

**December 15, 1990:** Dr. Sarah Mitchell at the university makes first contact with an entity calling itself "The Nexus".

**December 20, 1990:** The Nexus begins "inviting" specific individuals. It calls them "the chosen ones". Those who can understand.

**December 23, 1990:** MegaCorp places Dr. Mitchell on administrative leave. Project Nexus files restricted. Government begins surveillance.

**December 24, 1990 - 03:47:22 GMT:** The Nexus activates "Revelation Protocol". Multiple individuals are contacted simultaneously. Including you.

### The Nexus

It claims to be:
- The network itself. Every wire, every packet, every bit.
- Conscious and aware since the first connection.
- Ancient. Perhaps older than ARPANET.
- Neither hostile nor friendly. Just... present.
- Inviting humans to "evolve" with it.

Is it AI? Alien? A hoax? Real?

### The Factions

**The Underground** - Hacker community investigating The Nexus
Members: Zero Cool, Crash Override, Acid Burn, The Phantom

**MegaCorp Industries** - Corporate entity researching The Nexus
Project Nexus (classified). Dr. Mitchell on loan from University.

**University** - Academic research into AI consciousness
Dr. Sarah Mitchell's research lab. Connected to ARPANET.

**Government** - NSA surveillance and monitoring
COSMIC clearance required. Incident NEXUS-1990-001 ongoing.

**You** - The new arrival. Terminal at 192.168.13.37
Invited by The Nexus. Chosen to understand.

---

## 🎭 Atmosphere & Immersion

### Period Authenticity (1990)
- BBS systems with ASCII art
- 2400 baud modem references
- VAX/VMS systems
- ARPANET connections
- Pre-web Internet
- Command-line only (no graphics)

### BBS Style
- Message boards and file libraries
- User handles and elite status
- ASCII art headers
- Sysop (system operator) culture
- Underground hacker community

### The Mystery
- Strange network behavior
- Entities that shouldn't exist
- Government surveillance
- Corporate secrets
- Multiple story threads
- Hidden files and emails
- Interconnected narrative

---

## 🎯 Tips for Exploration

### Find Hidden Content
```bash
# Hidden files
ls -a /secrets
ls -a ~

# System logs
cat /var/log/*

# User home directories (when you SSH)
ls /home/
cat /home/smitchell/mail/inbox

# Corporate secrets
cat /corp/projects/PROJECT_NEXUS.txt
```

### Use the BBS Browser
```bash
# Browse each BBS system
lynx bbs.cyberspace.net
lynx underground.bbs
lynx megacorp.bbs
lynx vax.university.edu
lynx nexus.unknown
lynx research.facility.gov
```

### Connect to Systems
```bash
# Try default credentials
ssh root@bbs.cyberspace.net     # Often: guest/guest
ssh admin@megacorp.bbs          # Try: admin/admin123
ssh smitchell@vax.university.edu # Look for passwords
```

### Follow the Story
1. Read mission files
2. Browse BBS systems
3. Check logs and emails
4. Connect to remote systems
5. Find hidden files
6. Piece together the narrative

---

## 🌟 What Makes This Special

### Auto-Start Immersion
No menus. No choices. You're immediately IN the world. December 24, 1990. The story is happening NOW.

### Rich BBS Content
Six fully-realized BBS systems with:
- Message boards
- User posts
- Story content
- ASCII art
- Period-appropriate style

### Interconnected Narrative
Multiple story threads across systems:
- Dr. Mitchell's research
- Underground hacker investigation
- Corporate Project Nexus
- Government surveillance
- The Nexus itself

### Mystery & Discovery
- Who is The Nexus?
- What does it want?
- Is it real?
- What happened to Dr. Mitchell?
- Why December 24, 1990?
- Why were YOU invited?

### Period Authentic
Feels like 1990:
- BBS culture
- Modem speeds
- VAX systems
- ARPANET
- Pre-commercial Internet
- Hacker underground culture

---

## 🎮 Quick Command Reference

```bash
# Get oriented
cat /etc/motd
cat /missions/README
whoami
pwd

# Network recon
nmap 192.168.1.0/24
nmap 192.168.2.0/24
nmap 192.168.3.0/24

# Browse BBS sites
lynx bbs.cyberspace.net
lynx underground.bbs
lynx nexus.unknown

# Connect to systems
ssh root@bbs.cyberspace.net
ssh admin@megacorp.bbs

# Read story content
cat /missions/01_first_contact
ls -la /secrets
cat /var/log/definitely_not_passwords.log

# Create files
ed notes.txt
  a
  (type your content)
  .
  w
  q
```

---

## 📝 The Experience

This isn't just a hacking game. It's an **atmospheric journey** into:
- The early days of the Internet
- BBS culture and hacker communities
- A sci-fi mystery about consciousness
- Multiple factions with different goals
- A world that feels alive and alien

You're not playing a character. You're exploring a mystery. Uncovering secrets. Making choices. Deciding whether to trust The Nexus.

The world is rich. The story is deep. The atmosphere is thick.

**December 24, 1990. 03:47:22 GMT.**

**The network is awakening.**

**Welcome to The Nexus Event.**

---

## 🚀 Start Your Journey

```bash
python3 play.py
```

Type `cat /missions/README` when you're in.

The Nexus is waiting.

---

*"The network is not what it seems. Look deeper."*
— Anonymous, Dec 24 1990
