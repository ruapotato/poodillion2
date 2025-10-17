# Quick Start Guide

## Run the Game

```bash
python3 demo.py
```

This launches the interactive hacking scenario. You'll start on an attacker system with a target at `192.168.1.50`.

## First Steps

1. **Read your notes**
   ```bash
   cat notes.txt
   ```

2. **Scan the target**
   ```bash
   nmap 192.168.1.50
   ```

3. **Look around**
   ```bash
   ls -la
   pwd
   ps -f
   ```

## Finding Vulnerabilities

The target system has several security issues:

### Method 1: Configuration Files
Web applications often store credentials in config files. Try finding web config files.

```bash
# Hint: Web servers typically store files in /var/www
# Look for .php, .env, or config files
```

### Method 2: Bash History
Users sometimes accidentally type passwords in commands. Check bash history files.

```bash
# Hint: Bash history is stored in .bash_history in user home directories
# Home directories are in /home/<username>
```

### Method 3: Vulnerable Processes
Some running processes have known vulnerabilities. Use `exploit` to attack them.

```bash
ps -f              # List all processes
exploit <pid> 50   # Attack a vulnerable process
```

## Advanced Techniques

### Pipe Commands
```bash
cat /etc/passwd | grep home
find / | grep password
```

### Search for Patterns
```bash
grep -i password /path/to/file
find /home -name "*.txt"
```

### Process Investigation
```bash
ps -f              # List processes with details
pstree             # Show process tree
kill -9 <pid>      # Kill a process
```

## Tips

- **Read everything**: Text files often contain clues
- **Check obvious places first**: Config files, history files, todo lists
- **Look for vulnerable services**: Web servers, databases, SSH
- **Escalate carefully**: Some actions might trigger defenses (future feature)
- **Use tab completion**: Type partial commands and hit Tab (in a full terminal)

## Common Commands Cheat Sheet

| Command | Purpose | Example |
|---------|---------|---------|
| `ls -la` | List all files with details | `ls -la /home` |
| `cat` | Read file contents | `cat /etc/passwd` |
| `grep` | Search for text | `grep password file.txt` |
| `find` | Find files | `find /home -name "*.txt"` |
| `ps -f` | List processes | `ps -f` |
| `exploit` | Attack process | `exploit 123 50` |
| `nmap` | Scan network/ports | `nmap 192.168.1.50` |
| `cd` | Change directory | `cd /home/webadmin` |
| `pwd` | Show current path | `pwd` |

## Winning Conditions

For now, the goal is to explore and learn. Future versions will have specific objectives like:
- Exfiltrate a specific file
- Gain root access on the target
- Plant a backdoor
- Cover your tracks

Have fun and happy hacking!
