# Bugs and Issues Found During Testing

## Critical Bugs (System Hangs)

### 1. ✅ FIXED: netd Infinite Loop Blocks Boot
**Status:** FIXED
**Description:** The `/sbin/netd` daemon has a `while True` loop that never exits, blocking the boot process.
**Impact:** Systems never finish booting, timeouts occur
**Fix Applied:** Changed netd to exit after initialization. Commented out infinite loop with explanation.

### 2. ✅ FIXED: execute_command() Hangs Indefinitely
**Status:** FIXED
**Description:** `UnixSystem.execute_command()` hung when trying to execute ANY command
**Impact:** Prevented all command testing and gameplay
**Location:** `scripts/bin/pooshell:173-183`
**Root Cause:**
- `/bin/pooshell` script didn't handle the `-c` option
- When `execute_command('pwd')` called `/bin/pooshell -c 'pwd'`, the script ignored the arguments
- It entered the interactive REPL loop with `while True` and `input(prompt)`
- Since there was no user to provide input, it hung indefinitely
**Fix Applied:** Added `-c` option handling to pooshell that executes the command and exits immediately


## Medium Priority Issues

### 3. Network Routing Not Tested
**Status:** Cannot test due to #2
**Description:** Multi-hop routing through routers not verified end-to-end
**Impact:** Unknown if routing actually works in practice

### 4. SSH Command Not Tested
**Status:** Cannot test due to #2
**Description:** SSH between systems not verified
**Impact:** Unknown if SSH mechanism works

### 5. Ping Command May Not Work
**Status:** Cannot test due to #2
**Description:** Ping relies on ICMP packets and netd processing
**Impact:** Basic connectivity testing unavailable

## Low Priority Issues

### 6. netd Not Actually Running
**Status:** By design (for now)
**Description:** netd exits immediately instead of running continuously
**Impact:** Packet routing happens on-demand, not asynchronously
**Note:** This is acceptable for a game, but less realistic

### 7. No Background Process Support
**Status:** Architectural limitation
**Description:** Daemons can't run in background continuously
**Impact:** Less realistic, but acceptable for game

## Architecture Issues

### 8. PooScript Execution Model
**Status:** Needs investigation
**Description:** Not clear how PooScript scripts should behave (blocking vs non-blocking)
**Impact:** Affects all command execution

### 9. Device File Callbacks
**Status:** May be causing hangs
**Description:** VFS device handlers may be waiting for input
**Impact:** Could be root cause of #2

## Testing Blockers

**Current Status:** Cannot test ANY gameplay because execute_command() hangs

**Next Steps:**
1. Debug execute_command() and Shell.execute()
2. Check /bin/pooshell for infinite loops
3. Verify VFS callbacks don't block
4. Add timeout mechanism to prevent hangs
5. Test commands one by one

## Test Results Summary

✅ **Working:**
- System creation
- Network adapter
- Physical network topology
- VFS file creation
- Device file creation
- System boot (with background netd daemon)
- User login
- Command execution (FIXED!)
- Shell interaction
- Background daemon support

🔄 **Needs Testing:**
- Network routing (multi-hop)
- SSH between systems
- Ping/ICMP
- Network commands (ifconfig, nmap, etc.)
- Full scenario gameplay

**Status:** Core functionality restored! System is now playable. Need to test network features.

## Recommended Fix Order

1. ✅ **COMPLETED:** Fix execute_command() hang
2. ✅ **COMPLETED:** Implement background daemon support
3. 🔄 **IN PROGRESS:** Test basic commands (ls, cat, pwd, etc.)
4. **NEXT:** Test network commands (ifconfig, ping)
5. **NEXT:** Test SSH functionality
6. **NEXT:** Test multi-hop routing
7. **LATER:** Optimize performance
8. **LATER:** Add more Unix commands

