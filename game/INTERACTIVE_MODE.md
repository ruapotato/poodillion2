# Interactive Mode - Better Ways to Play

## Problem Solved

The old way of testing was clunky - you had to dump all commands at once into stdin. Now we have **proper interactive modes** where you can:

- Run commands one at a time
- See output immediately
- Run follow-up commands based on results
- Experience a **living, breathing world** with background activity

## New Ways to Play

### 1. Interactive Test Mode (Recommended)

```bash
./interactive_test.py
```

**Features:**
- ✅ Proper REPL with command history (UP/DOWN arrows)
- ✅ Colored output and prompts
- ✅ **Background events** - the world is alive!
- ✅ Special commands: `status`, `events`, `notify on/off`
- ✅ Real-time network activity notifications
- ✅ Simulated users on the network

**Special Commands:**
```bash
help          # Show all commands
status        # Show network status, active users, recent events
events        # Show last 10 network events
notify on/off # Toggle event notifications
exit          # Quit
```

**Example Session:**
```
root@kali-box:~$ status

NETWORK STATUS:
  • 7 remote systems online
  • 7 web servers running (httpd)
  • 10 users active on network (simulated)
  • Your IP: 192.168.13.37

  RECENT NETWORK ACTIVITY:
    [11:30:15] [BBS] Elite hacker spotted on nexus.unknown
    [11:30:22] User 'zero_cool' logged into underground.bbs

root@kali-box:~$ lynx underground.bbs

[11:30:45] NETWORK EVENT: The Nexus pulse detected across all networks

root@kali-box:~$
```

### 2. Automated Demo

```bash
./demo.py
```

**Features:**
- 📽️ Guided walkthrough of all features
- ⏸️ Pauses with explanations
- ⌨️ Simulated typing effect
- 🎯 Shows best practices

**Perfect for:**
- First-time players
- Showcasing the game
- Learning the commands
- Understanding the story

### 3. Original Play Mode

```bash
./play.py
```

The full game experience with:
- Complete intro sequence
- Mission briefings
- SSH support
- All systems booting

## What Makes It "Alive"?

### Background Activity (`core/world_life.py`)

The world now has a **life system** that generates:

**1. Simulated Users**
- 10+ users active on various BBSs
- Users like: `zero_cool`, `acid_burn`, `crash_override`
- Login/logout events
- Different users on different systems

**2. Random Events**
Every few commands, something might happen:
- User logins: "User 'phantom' joined underground.bbs"
- BBS posts: "Strange network activity reported"
- Network scans: "Network scan detected from 192.168.3.100"
- Mysterious activity: "The Nexus pulse detected"

**3. Event Types**
- `user_login` - Someone logs in
- `bbs_post` - New message on BBS
- `network_scan` - Port scan detected
- `mysterious_activity` - The Nexus doing... something

**4. Visibility**
- Some events are visible to you (👁)
- Some are hidden (🔒) - happening in the background
- Use `events` command to see all recent activity

### Dynamic Content

Web pages can show real-time data:
- `/www/time.poo` - Current time (changes every request)
- `/www/serverinfo.poo` - Live server stats
- User counts update dynamically
- Content generated on-the-fly

## Comparison

| Feature | Old Way | Interactive Mode | Demo Mode |
|---------|---------|------------------|-----------|
| Command input | All at once | One at a time | Automated |
| See output | After all done | Immediate | With pauses |
| Follow-up commands | ❌ No | ✅ Yes | N/A |
| Command history | ❌ No | ✅ Yes | N/A |
| Background events | ❌ No | ✅ Yes | ✅ Some |
| Colored output | ❌ No | ✅ Yes | ✅ Yes |
| Status commands | ❌ No | ✅ Yes | ✅ Yes |
| Event notifications | ❌ No | ✅ Yes | ❌ No |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Interactive Test                       │
│                 (interactive_test.py)                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐         ┌──────────────────┐         │
│  │   REPL Loop  │◄────────►│   WorldLife      │         │
│  │              │         │  - Events        │         │
│  │ - Commands   │         │  - Simulated     │         │
│  │ - History    │         │    users         │         │
│  │ - Colors     │         │  - Network       │         │
│  └──────────────┘         │    activity      │         │
│         │                 └──────────────────┘         │
│         │                          │                    │
│         ▼                          ▼                    │
│  ┌──────────────────────────────────────┐              │
│  │        Virtual World (1990)          │              │
│  │  - 8 systems                         │              │
│  │  - 7 web servers (httpd)             │              │
│  │  - Network routing                   │              │
│  │  - Dynamic content (.poo)            │              │
│  └──────────────────────────────────────┘              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Tips for Interactive Mode

1. **Use `status` often** - See what's happening on the network

2. **Watch for events** - They give hints about the world
   ```
   [11:30:45] NETWORK EVENT: Strange packets from 192.168.99.1
   ```

3. **Explore thoroughly** - Try different combinations:
   ```bash
   lynx bbs.cyberspace.net
   lynx bbs.cyberspace.net/time.poo
   lynx underground.bbs
   ```

4. **Follow the events** - If you see "Elite hacker on nexus.unknown", maybe:
   ```bash
   ping 192.168.99.1
   lynx nexus.unknown
   nmap 192.168.99.1
   ```

5. **Turn off notifications if needed**:
   ```bash
   notify off   # Focus mode
   notify on    # Re-enable
   ```

## Future Enhancements

Possible additions:
- [ ] Time-based events (certain things happen at certain times)
- [ ] NPC behavior (bots that do things autonomously)
- [ ] Network traffic visualization
- [ ] Achievement/progress tracking
- [ ] Multiplayer support?
- [ ] Save/load game state
- [ ] More event types (attacks, breaches, discoveries)

## Technical Notes

**WorldLife System** (`core/world_life.py`):
- Maintains list of simulated users per system
- Generates random events every 5-10 seconds
- Events have timestamps and visibility flags
- Can generate dynamic content for pages

**Event Generation**:
```python
# 30% chance each update cycle (every 5+ seconds)
if random.random() < 0.3:
    event = generate_random_event()

# Event types: user_login, bbs_post, network_scan, mysterious_activity
```

**Integration**:
- Interactive test checks for events every 3 commands
- Events can interrupt command flow (notifications)
- All events logged for later viewing (`events` command)

## Conclusion

The interactive mode makes Brainhair feel like a **real, living world** instead of a static test environment. You can:

- ✅ Explore naturally
- ✅ React to events
- ✅ See the world changing
- ✅ Feel like part of a larger network

Try it now:
```bash
./interactive_test.py
```

Welcome to December 24, 1990. The network is alive. And it's waiting for you.
