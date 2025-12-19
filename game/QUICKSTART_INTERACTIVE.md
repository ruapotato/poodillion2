# Quick Start - Interactive Mode

## TL;DR

```bash
# Best way to play - Interactive mode with live events!
./interactive_test.py

# Or watch an automated demo
./demo.py

# Or play the full game
./play.py
```

## Interactive Mode - The Best Experience

### Start It Up

```bash
chmod +x interactive_test.py
./interactive_test.py
```

### What You'll See

```
╔═══════════════════════════════════════════════════════════════════╗
║            BRAINHAIR INTERACTIVE TEST ENVIRONMENT                ║
╚═══════════════════════════════════════════════════════════════════╝

INITIALIZING BRAINHAIR WORLD...

✓ World initialized
✓ Connected as root on kali-box (192.168.13.37)
✓ Background activity enabled

NETWORK STATUS:
  • 7 remote systems online
  • 7 web servers running (httpd)
  • 12 users active on network (simulated)
  • Your IP: 192.168.13.37

Type 'help' for commands, 'exit' to quit
TIP: The world is alive! Events happen in the background.

root@kali-box:~$
```

### First Commands

```bash
# See what's on the network
nmap 192.168.1.0/24

# Browse the web
lynx

# Visit specific sites
lynx underground.bbs
lynx bbs.cyberspace.net/serverinfo.poo

# Check network status
status

# View recent events
events

# Read missions
cat /missions/README
```

### Pro Tips

1. **Use UP/DOWN arrows** - Command history works!

2. **Watch for events** - The world is alive:
   ```
   [11:30:45] NETWORK EVENT: Elite hacker spotted on nexus.unknown
   ```

3. **Status command** - Your best friend:
   ```bash
   status   # Shows everything happening
   ```

4. **Toggle notifications**:
   ```bash
   notify off   # Focus mode
   notify on    # See events as they happen
   ```

5. **Follow your curiosity** - If you see an event about nexus.unknown, go investigate!

## What's Different?

### Old Way (Painful)
```bash
echo "ls
pwd
lynx
exit" | ./play.py
```
❌ All commands at once
❌ No follow-up possible
❌ Static world
❌ Can't react to output

### New Way (Fun!)
```bash
./interactive_test.py
```
✅ Commands one at a time
✅ See output immediately
✅ **Living world with events**
✅ React and explore naturally
✅ Command history
✅ Colored output
✅ Status commands

## The Living World

### Simulated Users
- 12+ users active across BBSs
- Names like: `zero_cool`, `acid_burn`, `crash_override`
- They login/logout
- Post on BBSs
- Scan networks

### Random Events
Every few commands, something might happen:

```
[11:30:15] NETWORK EVENT: User 'phantom' joined underground.bbs
[11:30:22] NETWORK EVENT: [BBS] Strange packets from 192.168.99.1
[11:30:45] NETWORK EVENT: The Nexus pulse detected
```

### Dynamic Content
Web pages change:
```bash
lynx bbs.cyberspace.net/time.poo    # Shows current time
lynx bbs.cyberspace.net/serverinfo.poo   # Live server stats
```

## Full Command Reference

### Special Commands
```bash
help          # Show help
status        # Network status + recent events
events        # Last 10 events (hidden + visible)
notify on/off # Toggle event notifications
exit          # Quit (or Ctrl+D)
```

### Exploration
```bash
lynx [site]              # Browse web
nmap <subnet>            # Scan network
ping <ip>                # Check if alive
ssh <ip>                 # Connect (coming soon)
```

### System
```bash
ls, cd, pwd              # Navigation
cat <file>               # Read files
ps                       # List processes
ifconfig                 # Network config
```

### Missions
```bash
cat /missions/README     # View missions
cat /missions/01_first_contact
cat /missions/05_the_nexus
```

## Example Session

```bash
$ ./interactive_test.py

root@kali-box:~$ status
  • 7 remote systems online
  • 7 web servers running (httpd)
  • 12 users active on network

root@kali-box:~$ nmap 192.168.1.0/24
Found hosts:
  192.168.1.10 (bbs.cyberspace.net)
  192.168.1.11 (underground.bbs)

[11:30:15] NETWORK EVENT: User 'zero_cool' logged into underground.bbs

root@kali-box:~$ lynx underground.bbs
[Shows Underground BBS content...]

root@kali-box:~$ events
  👁 [11:30:15] User 'zero_cool' logged into underground.bbs
  👁 [11:30:22] [BBS] Strange activity on nexus.unknown
  🔒 [11:30:30] Network scan from 192.168.3.100

root@kali-box:~$ ping 192.168.99.1
PING 192.168.99.1...
64 bytes from 192.168.99.1: seq=1 ttl=64 time=1.2ms

[11:31:00] NETWORK EVENT: The Nexus is watching...

root@kali-box:~$ lynx nexus.unknown
[Mysterious content...]

root@kali-box:~$ exit
See you in cyberspace, traveler.
```

## Demo Mode

Want to see everything without typing?

```bash
./demo.py
```

It will:
- Show network discovery
- Browse websites
- Display dynamic content
- Show missions
- Reveal the Nexus mystery
- Explain everything with pauses

Perfect for:
- First time exploring
- Showing off to others
- Learning the commands

## Troubleshooting

**Q: Events not appearing?**
```bash
notify on    # Make sure notifications are on
status       # Check recent events manually
```

**Q: Commands not working?**
```bash
help         # See all commands
ls /bin      # See available binaries
```

**Q: Want to start over?**
```bash
exit         # Quit
./interactive_test.py   # Restart (fresh world)
```

## Next Steps

Once you're comfortable:

1. **Try the missions**
   ```bash
   cat /missions/01_first_contact
   ```

2. **Explore all BBSs**
   ```bash
   lynx underground.bbs
   lynx megacorp.bbs
   lynx nexus.unknown
   ```

3. **Investigate the Nexus**
   - Why are there events from 192.168.99.1?
   - What is "The Nexus"?
   - What's happening on December 24, 1990?

4. **Try dynamic content**
   ```bash
   lynx bbs.cyberspace.net/time.poo
   lynx bbs.cyberspace.net/serverinfo.poo
   ```

## Files Created

- `interactive_test.py` - Main interactive mode
- `demo.py` - Automated walkthrough
- `core/world_life.py` - Living world system
- `INTERACTIVE_MODE.md` - Full documentation
- `QUICKSTART_INTERACTIVE.md` - This file

## Have Fun!

The network is waiting. December 24, 1990. Something is happening.

Are you ready to explore?

```bash
./interactive_test.py
```

🌐 Welcome to cyberspace.
