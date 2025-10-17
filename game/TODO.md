# Poodillion TODO - Making it the Ultimate 1990s Hacking Sandbox

## PRIORITY 1: Tool Building & Replacement (THE CORE FEATURE)

### Make it obvious that tools are editable
- [x] PooScript already implemented
- [ ] Add prominent `/root/README` explaining tool building
- [ ] Add `/usr/doc/BUILDING.md` with comprehensive guide
- [ ] Make shell welcome message emphasize "ALL TOOLS ARE EDITABLE!"
- [ ] Add example in MOTD showing how to modify a tool

### Source code examples
- [ ] Create `/usr/src/examples/` directory
  - [ ] `hello.poo` - Simple hello world
  - [ ] `calculator.poo` - Basic calculator
  - [ ] `mygrep.poo` - Reimplementation of grep
  - [ ] `counter.poo` - File counter utility
  - [ ] `logger.poo` - Log file analyzer
  - [ ] `backup.poo` - Backup script
  - [ ] `monitor.poo` - System monitor
  - [ ] `scanner.poo` - Port scanner
  - [ ] `exploit.poo` - Exploit framework template
  - [ ] `README` - How to build and install tools

### Build system
- [ ] Implement `/bin/make` command
  - [ ] Parse simple Makefiles
  - [ ] Support basic targets (all, install, clean)
  - [ ] Run commands from rules
- [ ] Add example Makefiles in `/usr/src/examples/`
- [ ] Implement `/bin/install` command
  - [ ] Copy files to destinations
  - [ ] Set permissions automatically
  - [ ] Backup old versions (optional -b flag)

### Compiler/interpreter tools
- [ ] `/bin/pooc` - PooScript "compiler" (validator/installer)
- [ ] `/bin/lint` - PooScript syntax checker
- [ ] `/bin/debug` - Simple debugger for PooScripts

---

## PRIORITY 2: Package Manager & Repository (NEW!)

### Package Manager Implementation
- [ ] Design package format (`.poo-pkg` or similar)
  - [ ] Metadata (name, version, description, dependencies)
  - [ ] Files to install (binaries, docs, configs)
  - [ ] Install/remove scripts
  - [ ] Checksums for integrity
- [ ] Implement `/bin/pooget` command (like apt-get but Poodillion-style!)
  - [ ] `pooget install <name>` - Install package
  - [ ] `pooget remove <name>` - Remove package
  - [ ] `pooget update` - Update package list
  - [ ] `pooget upgrade` - Upgrade installed packages
  - [ ] `pooget search <term>` - Search packages
  - [ ] `pooget list` - List installed packages
  - [ ] `pooget info <name>` - Show package info
- [ ] Package database in `/var/lib/pooget/`
  - [ ] Installed packages registry
  - [ ] Available packages cache
  - [ ] Lock file for concurrent operations

### Online Repository
- [ ] Create remote package server system
  - [ ] Add `packages.repo.net` (192.168.6.10) to world
  - [ ] HTTP-based package index
  - [ ] Downloadable .poo-pkg files
- [ ] Repository metadata
  - [ ] `/repo/PACKAGES.txt` - Package list
  - [ ] `/repo/packages/<name>/<version>/<name>.poo-pkg` - Package files
  - [ ] `/repo/categories.txt` - Package categories
- [ ] Implement HTTP package download
  - [ ] Use existing `curl`/`http-get` infrastructure
  - [ ] Handle package verification
  - [ ] Show download progress

### Package Categories & Content
- [ ] **utils/** - Utility packages
  - [ ] `utils-extra` - Additional text utilities
  - [ ] `filemanager` - Enhanced file management
  - [ ] `compression` - tar, gzip, bzip2
- [ ] **net/** - Networking packages
  - [ ] `nettools-advanced` - Advanced networking
  - [ ] `ftp-client` - FTP client
  - [ ] `irc-client` - IRC client
  - [ ] `finger-server` - Finger daemon
  - [ ] `telnet-server` - Telnet daemon
- [ ] **games/** - Classic Unix games
  - [ ] `games-bsd` - BSD games collection
  - [ ] `adventure` - Colossal Cave Adventure
  - [ ] `nethack` - NetHack roguelike
  - [ ] `rogue` - Classic Rogue
- [ ] **hacking/** - Hacking tools (fun stuff!)
  - [ ] `exploit-db` - Exploit database
  - [ ] `metasploit-lite` - Basic exploitation framework
  - [ ] `password-crackers` - Password cracking tools
  - [ ] `sniffers` - Network sniffers
- [ ] **dev/** - Development tools
  - [ ] `build-essential` - Make, compilers, etc.
  - [ ] `pooscript-dev` - Development tools for PooScript
  - [ ] `debugger` - Debugging tools

### Attack Surface (Security Vulnerabilities)
- [ ] **Buffer overflow in package parser**
  - [ ] Malicious package with oversized fields crashes pkg
  - [ ] Can be exploited for privilege escalation
- [ ] **Path traversal in package extraction**
  - [ ] Package with `../../etc/passwd` in paths
  - [ ] Can overwrite system files
- [ ] **Unsigned packages**
  - [ ] No signature verification
  - [ ] Man-in-the-middle attacks possible
  - [ ] Repository compromise leads to backdoored packages
- [ ] **Dependency confusion**
  - [ ] Malicious package masquerading as dependency
  - [ ] Install pulls wrong package
- [ ] **SUID binary in package**
  - [ ] Package installs SUID root binary with vulnerability
  - [ ] Instant privilege escalation
- [ ] **Post-install script execution**
  - [ ] Post-install runs as root
  - [ ] Malicious packages can backdoor system
- [ ] **Race condition in package lock**
  - [ ] Concurrent pkg operations cause corruption
  - [ ] Can lead to broken system or privilege escalation
- [ ] **Symlink attacks during install**
  - [ ] Package tricks installer into following symlinks
  - [ ] Overwrites arbitrary files
- [ ] **Repository poisoning mission**
  - [ ] Player discovers they can upload to repository
  - [ ] Create backdoored version of popular package
  - [ ] Wait for others (NPCs) to install it
- [ ] **Supply chain attack scenario**
  - [ ] Upstream repo compromised
  - [ ] Popular package backdoored
  - [ ] Player must detect and clean infection

### Repository Management Tools
- [ ] `/usr/sbin/repo-admin` - Repository management (on server)
  - [ ] Add/remove packages
  - [ ] Rebuild index
  - [ ] Sign packages (if we add signatures)
- [ ] `/usr/bin/pooget-build` - Create .poo-pkg files
  - [ ] Package creation from directory
  - [ ] Metadata editing
  - [ ] Validation
- [ ] Add to missions: "Upload your own package to repo"

### Auto-Update System (THE KILLER FEATURE!)
- [ ] **Automatic update daemon on all systems**
  - [ ] `/usr/sbin/pooget-autoupdate` daemon
  - [ ] Runs in background on all NPC systems
  - [ ] Checks for updates every ~5 minutes (configurable)
  - [ ] Automatically installs security updates
  - [ ] Logs all activity to `/var/log/pooget-autoupdate.log`
- [ ] **Configuration**
  - [ ] `/etc/pooget/autoupdate.conf` - Enable/disable, frequency, repo URL
  - [ ] Some systems more aggressive (update every 2 min)
  - [ ] Some systems more cautious (update every 10 min)
  - [ ] Player's system has it DISABLED by default (or optional)
- [ ] **Observable behavior**
  - [ ] Network traffic when systems check for updates
  - [ ] Log entries: "Checking for updates...", "Installing package X..."
  - [ ] Process visible in `ps` output
  - [ ] Can see it with `tail -f /var/log/pooget-autoupdate.log`
  - [ ] WorldLife events: "System X installed package Y"
- [ ] **Attack gameplay loop**
  1. Player discovers repo server is world-writable (vulnerability!)
  2. Player creates backdoored package (e.g., backdoor-ls that hides files)
  3. Player uploads to repo replacing legitimate package
  4. Wait 5-10 minutes...
  5. Watch other systems auto-update and install YOUR backdoor
  6. Now you can access those systems with your backdoor!
- [ ] **Advanced attack scenarios**
  - [ ] Backdoor common tools (ls, ps, netstat) to hide your presence
  - [ ] Backdoor login/ssh to capture passwords
  - [ ] Install keyloggers via package updates
  - [ ] Create botnet by backdooring all systems
  - [ ] Race condition: upload malicious package just before university system updates
- [ ] **Detection mechanics**
  - [ ] Sysadmin NPC might notice suspicious package changes
  - [ ] Checksums might not match (if they're checking)
  - [ ] Network monitoring might show unusual traffic
  - [ ] Your backdoor might be obvious if not well hidden
- [ ] **Integration with world_life.py**
  - [ ] Generate events when systems update
  - [ ] "underground.bbs installed security-updates"
  - [ ] "vax.university.edu upgraded 3 packages"
  - [ ] Player can monitor and time their attacks

---

## PRIORITY 3: Missing Core Unix Tools

### Text processing
- [ ] `head` - Show first N lines
- [ ] `tail` - Show last N lines (bonus: `tail -f` for follow)
- [ ] `more` / `less` - Pagers
- [ ] `wc` - Word/line/character count
- [ ] `sort` - Sort lines
- [ ] `uniq` - Remove duplicates
- [ ] `cut` - Extract columns
- [ ] `tr` - Translate/delete characters
- [ ] `awk` - Pattern scanning (simplified)
- [ ] `sed` - Stream editor (basic version)
- [ ] `diff` - Compare files
- [ ] `patch` - Apply diffs
- [ ] `strings` - Extract strings from binaries
- [ ] `od` / `hexdump` - Octal/hex dump

### File operations
- [ ] `tar` - Tape archive
- [ ] `compress` / `uncompress` - Compression
- [ ] `gzip` / `gunzip` - GNU zip
- [ ] `file` - Determine file type
- [ ] `ln` - Create links (hard & symbolic)
- [ ] `dd` - Disk/data copy

### System management
- [ ] `top` - Real-time process monitor
- [ ] `free` - Memory usage
- [ ] `df` - Disk free space
- [ ] `du` - Disk usage
- [ ] `mount` / `umount` - Mount filesystems
- [ ] `dmesg` - Kernel messages
- [ ] `sysctl` - Kernel parameters
- [ ] `lsmod` / `insmod` / `rmmod` - Kernel modules
- [ ] `nice` / `renice` - Process priority
- [ ] `cron` / `at` - Job scheduling

### User management
- [ ] `who` - Who is logged in
- [ ] `w` - Who and what they're doing
- [ ] `users` - List users
- [ ] `last` - Login history
- [ ] `finger` - User information
- [ ] `write` - Send message to user
- [ ] `wall` - Broadcast to all users
- [ ] `talk` - Interactive chat
- [ ] `mesg` - Allow/deny messages

### Communication & networking
- [ ] `mail` / `pine` - Email clients
- [ ] `telnet` - Interactive telnet
- [ ] `ftp` - FTP client
- [ ] `gopher` - Gopher client
- [ ] `archie` - FTP search
- [ ] `veronica` - Gopher search
- [ ] `irc` - IRC client
- [ ] `nn` / `tin` - USENET newsreaders

---

## PRIORITY 4: Documentation System

### Create /usr/doc/ hierarchy
- [ ] `/usr/doc/commands.txt` - List all commands with descriptions
- [ ] `/usr/doc/pooscript.txt` - PooScript language reference
- [ ] `/usr/doc/hacking.txt` - Hacking guide for the game
- [ ] `/usr/doc/network.txt` - Network commands and concepts
- [ ] `/usr/doc/building.txt` - How to build and install tools
- [ ] `/usr/doc/packages.txt` - Package manager guide
- [ ] `/usr/doc/security.txt` - System security (ironically)
- [ ] `/usr/doc/missions.txt` - Mission hints and guide

### Implement man command
- [ ] `/bin/man` - Manual page viewer
  - [ ] Read from `/usr/doc/man/` or inline documentation
  - [ ] Format and display nicely
  - [ ] `man ls` shows ls usage
  - [ ] `man -k <keyword>` searches manpages
- [ ] Create man pages for all commands
  - [ ] Generate from PooScript comments?
  - [ ] Or hand-write key ones

### Help system improvements
- [ ] Add `--help` flag support to all commands
- [ ] Add `-h` short flag
- [ ] Consistent help format across all tools
- [ ] `help` command that lists all available commands by category

---

## PRIORITY 5: Authentic System Files

### /etc/ configuration files
- [ ] `/etc/motd` - Message of the day (shown at login)
- [ ] `/etc/services` - Network services list
- [ ] `/etc/protocols` - Network protocols list
- [ ] `/etc/profile` - System-wide shell initialization
- [ ] `/etc/environment` - Environment variables
- [ ] `/etc/rc.local` - Startup script
- [ ] `/etc/issue.net` - Network login banner
- [ ] `/etc/hosts.allow` / `/etc/hosts.deny` - TCP wrappers

### /var/ variable data
- [ ] `/var/log/messages` - System log (with authentic 1990s entries)
- [ ] `/var/log/wtmp` - Login records
- [ ] `/var/log/lastlog` - Last login per user
- [ ] `/var/log/auth.log` - Authentication log
- [ ] `/var/log/daemon.log` - Daemon logs
- [ ] `/var/spool/mail/` - Mail directory with mailboxes
- [ ] `/var/spool/news/` - USENET news spool
- [ ] `/var/run/` - Runtime data (PIDs, sockets)
- [ ] `/var/tmp/` - Temporary files (persistent across reboot)

### /tmp/ with realistic temp files
- [ ] Random temp files from "other users"
- [ ] `.X11-unix/` - X11 sockets
- [ ] Session files
- [ ] Lock files

### User home directories
- [ ] `/home/phantom/` - Underground hacker
  - [ ] `.bash_history` with interesting commands
  - [ ] Personal files, notes, secrets
- [ ] `/home/zero_cool/` - Elite hacker
- [ ] `/home/acid_burn/` - Another hacker
- [ ] `/home/student42/` - University student
- [ ] Each with realistic files, history, mail

### Root home directory
- [ ] `/root/.bash_history` - Command history
- [ ] `/root/.profile` - Shell initialization
- [ ] `/root/README` - Getting started guide

---

## PRIORITY 6: Classic Unix Games

### Implement in /usr/games/
- [ ] `adventure` - Colossal Cave Adventure (text adventure)
- [ ] `rogue` - Classic roguelike dungeon crawler
- [ ] `nethack` - More advanced roguelike
- [ ] `hunt` - Multi-player hunt game
- [ ] `worm` - Snake game
- [ ] `trek` - Star Trek game
- [ ] `robots` - Avoid the robots
- [ ] `hangman` - Hangman word game
- [ ] `arithmetic` - Math quiz game
- [ ] `quiz` - Trivia quiz
- [ ] `tetris` - Tetris (if possible with ASCII)
- [ ] `snake` - Another snake variant
- [ ] `maze` - Random maze generator

### Game integration
- [ ] Some games have hints about the main plot
- [ ] Hidden commands or Easter eggs in games
- [ ] High score files in `/var/games/`
- [ ] Maybe a game is actually a disguised hacking tool?

---

## PRIORITY 7: Enhanced Network Services (1990s Authentic)

### Add new network systems
- [ ] `ftp.archive.net` (192.168.7.10) - FTP archive server
  - [ ] Anonymous FTP
  - [ ] Software archives
  - [ ] Login with username/password
- [ ] `gopher.university.edu` (192.168.7.20) - Gopher server
  - [ ] Gopher menu system
  - [ ] Documents and directories
  - [ ] Links to other gophers
- [ ] `irc.undernet.org` (192.168.7.30) - IRC server
  - [ ] Join channels
  - [ ] Chat with bots/NPCs
  - [ ] Hidden channels with secrets
- [ ] `news.usenet.org` (192.168.7.40) - USENET server
  - [ ] Newsgroups (alt.hackers, comp.security, etc.)
  - [ ] Posted messages with clues
  - [ ] Some controversial/mysterious posts

### Service implementations
- [ ] `/bin/ftp` client
- [ ] `/bin/gopher` client
- [ ] `/bin/irc` client
- [ ] `/bin/nn` or `/bin/tin` newsreader
- [ ] `/bin/archie` - Search FTP archives
- [ ] `/bin/veronica` - Search Gopherspace

### Finger servers
- [ ] Finger daemon on multiple systems
- [ ] `finger @host` shows logged-in users
- [ ] `finger user@host` shows user info
- [ ] Some users have mysterious .plan files

---

## PRIORITY 8: World Building & Immersion

### More realistic network activity
- [ ] Expand `world_life.py` events
- [ ] Add more user types (sysadmins, students, hackers, bots)
- [ ] Realistic login/logout patterns
- [ ] Services starting/stopping
- [ ] System maintenance messages
- [ ] Network outages/problems

### Expand /missions/
- [ ] More detailed mission briefings
- [ ] Mission 01: First Contact (already exists?)
- [ ] Mission 02: Package Installation
- [ ] Mission 03: Build Your First Tool
- [ ] Mission 04: Repository Infiltration
- [ ] Mission 05: The Nexus (already exists?)
- [ ] Mission 06: Supply Chain Attack
- [ ] Mission 07: Root the Government Server
- [ ] Mission 08: The Final Convergence

### Add lore and story
- [ ] More /secrets/ files scattered around
- [ ] Email messages in `/var/spool/mail/`
- [ ] USENET posts with story clues
- [ ] IRC logs in user home directories
- [ ] BBS posts that develop the narrative
- [ ] Mysterious files that appear over time

### NPCs and bots
- [ ] Simulated users that respond to actions
- [ ] IRC bots you can interact with
- [ ] Sysadmin that notices suspicious activity
- [ ] Other "hackers" competing for objectives
- [ ] The Nexus as an AI antagonist/ally?

---

## PRIORITY 9: Improved Shell & UX

### Better error messages
- [x] More helpful "command not found" (already good!)
- [ ] Suggest similar commands
- [ ] Offer to install missing packages
  - [ ] "Command 'netcat' not found. Try: pooget install netcat"

### Shell improvements
- [ ] Tab completion (if interactive mode supports it)
- [ ] Command aliases (`ll` for `ls -l`)
- [ ] Shell functions
- [ ] Better job control (`fg`, `bg`, `jobs`)
- [ ] Command substitution with backticks or `$()`
- [ ] History substitution (`!!`, `!$`, `!n`)

### Colorization
- [ ] Colored ls output (directories blue, executables green)
- [ ] Syntax highlighting in less/more
- [ ] Colored diff output
- [ ] Colored grep matches

### Terminal improvements
- [ ] Clear screen (`clear` command)
- [ ] Terminal resizing support
- [ ] Better ANSI escape code handling

---

## PRIORITY 10: Polish & Easter Eggs

### ASCII art everywhere
- [ ] Boot screen with ASCII art logo
- [ ] Login banner with figlet text
- [ ] MOTD with ASCII art
- [ ] `fortune | cowsay` combos (fortune exists?)
- [ ] BBS systems with ANSI art
- [ ] Hidden ASCII art files

### Easter eggs
- [ ] Secret commands only found by reading source
- [ ] Hidden directories (maybe `/proc/nexus/`)
- [ ] Backdoors in tools (discover and exploit them!)
- [ ] Time-based events (Dec 24, 1990 has special behavior)
- [ ] Konami code equivalent?
- [ ] Developer messages in file comments

### Period-appropriate slang
- [ ] More 1990s/cyberpunk terminology
- [ ] "Bogus!" for errors
- [ ] "Rad!" for success
- [ ] "Hosed!" for crashes
- [ ] l33t speak in underground BBS

### Fun commands
- [x] `cowsay` improvements
- [x] `lolcat` for rainbow text
- [x] `banner` for large text
- [ ] `figlet` for ASCII art text
- [x] `sl` (steam locomotive for typo)
- [x] `rev` reverse text
- [x] `yes` infinite output

---

## Implementation Strategy

### Phase 1: Foundation (Week 1)
1. Tool building documentation and examples
2. Package manager core implementation
3. Repository server setup
4. Basic packages

### Phase 2: Content (Week 2)
1. Missing core Unix tools
2. Documentation system
3. Authentic system files
4. More network services

### Phase 3: Fun Stuff (Week 3)
1. Classic games
2. Easter eggs
3. More missions
4. Attack surface scenarios

### Phase 4: Polish (Week 4)
1. Shell improvements
2. Better error messages
3. Colorization
4. Testing and bug fixes

---

## Testing Priorities

- [ ] Test all new tools thoroughly
- [ ] Verify package install/remove works correctly
- [ ] Test attack surface vulnerabilities (make sure they're exploitable!)
- [ ] Ensure all missions are completable
- [ ] Performance testing with many packages
- [ ] Network service stress testing

---

## Documentation to Create

- [ ] `PACKAGES.md` - Package system architecture
- [ ] `SECURITY.md` - Intentional vulnerabilities and exploits
- [ ] `MISSIONS.md` - All mission walkthroughs
- [ ] `API.md` - PooScript API reference
- [ ] `CONTRIBUTING.md` - How to add content

---

## Future Ideas (Post-MVP)

- [ ] Multiplayer support (multiple players in same world)
- [ ] Save/load game state
- [ ] Persistent world that evolves over time
- [ ] Kernel module system (like Linux LKMs)
- [ ] X Window System (text-mode "GUI")
- [ ] Virtualization (VM inside VM?)
- [ ] Container system (like Docker but 1990s style)
- [ ] Network packet crafting tools
- [ ] Full exploit development toolchain
- [ ] CTF (Capture The Flag) mode
- [ ] Achievements system
- [ ] Leaderboard for fastest mission completion

---

## Notes

- **Everything should be editable** - That's the core philosophy
- **Authentic 1990s feel** - No modern conveniences
- **Educational** - Teach real Unix/Linux concepts
- **Fun** - Not just a boring terminal simulator
- **Exploitable** - Security holes are features!
- **Discoverable** - Reward curiosity and exploration

---

*Last updated: 2025-10-16*
*This is a living document - add to it as new ideas emerge!*
