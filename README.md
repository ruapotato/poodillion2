# Poodillion 2: Virtual Unix Hacking Game

A terminal-based hacking game featuring a complete Unix-like operating system emulation written in pure Python. Set in the early 1990s, players navigate a realistic command-line environment to solve hacking challenges, exploit vulnerabilities, and infiltrate virtual networks.

## Features

### Complete Unix Emulation
- **Virtual Filesystem (VFS)**: Full Unix-style filesystem with inodes, permissions, directories, symbolic links, and device files
- **User & Permission System**: UID/GID-based permissions, user groups, SUID/SGID support
- **Process Management**: Process spawning, PIDs, process tree, signals (SIGTERM, SIGKILL, etc.)
- **Shell Parser**: Full command-line parsing with pipes (`|`), redirects (`>`, `>>`, `<`, `2>`), variables (`$VAR`), and background jobs (`&`)
- **Virtual Network**: Multi-system networking with firewall rules, port scanning, and inter-system connectivity

### Available Commands

#### Filesystem Commands
- `ls` - List directory contents (supports `-l`, `-a`)
- `cd` - Change directory
- `pwd` - Print working directory
- `cat` - Display file contents
- `mkdir` - Create directories
- `touch` - Create files or update timestamps
- `rm` - Remove files/directories
- `echo` - Print text
- `grep` - Search text patterns
- `find` - Search for files

#### Process Commands
- `ps` - List processes (supports `-a`, `-e`, `-f`)
- `kill` - Send signals to processes
- `killall` - Kill processes by name
- `pstree` - Display process tree
- `exploit` - **Game mechanic**: Attack vulnerable processes

#### Network Commands
- `ifconfig` - Show network interfaces
- `netstat` - Show network connections
- `nmap` - Scan networks and ports (**game mechanic**)
- `ssh` - Connect to remote systems (coming soon)

### Advanced Features
- **Pipe chaining**: `cat file.txt | grep password | grep -i admin`
- **Output redirection**: `echo "data" > file.txt`, `cat file1.txt >> file2.txt`
- **Shell variables**: `$PATH`, `$HOME`, `$USER`
- **Permission checking**: Realistic Unix permission enforcement
- **SUID execution**: Commands can run with elevated privileges

## Installation

No dependencies required! Just Python 3.7+

```bash
cd poodillion2
python3 demo.py
```

## Usage

### Basic Demo
```bash
python3 demo.py basic
```

Runs a series of commands to demonstrate the system.

### Interactive Hacking Scenario
```bash
python3 demo.py
```

Launches an interactive shell on an "attacker" system with a vulnerable target to compromise.

### Example Session
```
root@kali-box:~# ls
notes.txt

root@kali-box:~# cat notes.txt
Target: 192.168.1.50
Objective: Gain root access and exfiltrate data

root@kali-box:~# nmap 192.168.1.50
Starting Nmap 7.01 ( https://nmap.org )
Nmap scan report for 192.168.1.50
Host is up (0.00052s latency).

PORT     STATE SERVICE
22/tcp   open  ssh
80/tcp   open  http
3306/tcp open  mysql

root@kali-box:~# ps -f
UID        PID  PPID  C STIME   TIME CMD
root         1     0  0 00:00  00:00 init init
root         2     1  0 00:00  00:00 sh sh

root@kali-box:~# echo "test" | grep test
test
```

## Architecture

```
poodillion2/
├── core/
│   ├── vfs.py          # Virtual Filesystem (inodes, directories, files)
│   ├── permissions.py  # User/group/permission management
│   ├── process.py      # Process management (spawn, kill, signals)
│   ├── shell.py        # Shell parser and executor
│   ├── network.py      # Virtual network layer
│   └── system.py       # Main system class
├── commands/
│   ├── fs.py           # Filesystem commands
│   └── proc.py         # Process commands
├── demo.py             # Demo and interactive shell
└── README.md
```

## Game Mechanics

### Vulnerable Processes
Services can be tagged as `vulnerable`. Use the `exploit` command to attack them:

```bash
ps -f  # Find vulnerable processes
exploit 123 50  # Deal 50 damage to process 123
```

When a process health reaches 0, it's terminated.

### Network Infiltration
1. **Scan the network**: `nmap 192.168.1.0/24`
2. **Identify services**: `nmap <target_ip>`
3. **Find credentials**: Search config files, bash history, etc.
4. **Exploit vulnerabilities**: Use `exploit` on vulnerable services
5. **Escalate privileges**: Find SUID binaries, password files

### Hidden Clues
- `.bash_history` files may contain accidentally typed passwords
- Config files (`config.php`, `.env`) often have database credentials
- `todo.txt` files might reveal security weaknesses
- Process lists show running vulnerable services

## Roadmap

### Near-term
- [ ] SSH command to actually connect between systems
- [ ] More Unix commands (cp, mv, chmod, chown, etc.)
- [ ] Text editor (vi-like)
- [ ] More realistic network simulation
- [ ] Save/load game state

### Mid-term
- [ ] Terminal UI with multiple windows (using curses/rich)
- [ ] Level/scenario system
- [ ] Achievement system
- [ ] IDS (Intrusion Detection System) mechanics
- [ ] Time pressure / detection mechanics

### Long-term
- [ ] Scriptable AI opponents
- [ ] Multiplayer (co-op and competitive)
- [ ] Procedurally generated networks
- [ ] Custom scenario editor
- [ ] Campaign mode with narrative

## Design Philosophy

1. **Realistic**: Emulate real Unix behavior as accurately as possible
2. **Scriptable**: Everything should be automatable (AI-playable)
3. **Educational**: Teach real Unix commands and security concepts
4. **Fun**: Engaging gameplay with clear objectives
5. **Portable**: Pure Python, runs anywhere

## Contributing

This is a playground for experimentation! Some ideas:
- Add more Unix commands
- Create new hacking scenarios
- Implement a better terminal UI
- Add persistence (save/load)
- Create a tutorial system
- Add sound effects or ASCII art

## License

MIT License - hack away!

## Credits

Inspired by classic terminal hacking games and the desire to learn Unix internals through game development.

Built for the love of terminals, Unix philosophy, and the golden age of hacking games.
