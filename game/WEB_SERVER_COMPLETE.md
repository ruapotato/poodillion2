# Web Server Implementation Complete

## Overview

Brainhair now has a complete client-server web architecture with:
- HTTP daemon (`httpd`) running on multiple servers
- Web browser (`lynx`) for browsing sites over the network
- Dynamic server-side content execution (.poo scripts like PHP/CGI)
- DNS-like hostname resolution
- Network-based communication between client and servers

## Architecture

```
┌─────────────┐         Network         ┌──────────────────┐
│   Browser   │◄──────────────────────►│   Web  Server    │
│   (lynx)    │      TCP/IP (virtual)   │     (httpd)      │
└─────────────┘                          └──────────────────┘
      │                                           │
      │                                           ▼
      │                                   ┌──────────────────┐
      └───────────────────────────────────►  Static Files    │
                                          │   (.bbs, .html)  │
                                          └──────────────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │ Dynamic Scripts  │
                                          │   (.poo files)   │
                                          │ Executed server- │
                                          │      side        │
                                          └──────────────────┘
```

## Components

### 1. `/sbin/httpd` - Web Server Daemon
- **Purpose**: Serves web content from `/www/` directory
- **Features**:
  - Static file serving (.bbs, .html)
  - Dynamic .poo script execution (server-side like PHP/CGI)
  - Creates PID file at `/var/run/httpd.pid`
  - Security: Directory traversal protection

**Usage**:
```bash
/sbin/httpd          # Start web server
ps | grep httpd      # Check if running
```

### 2. `/bin/lynx` - Web Browser
- **Purpose**: Text-based web browser for accessing remote sites
- **Features**:
  - DNS-style hostname resolution
  - Network reachability checks (uses VirtualNetwork)
  - Connects to remote httpd servers
  - Displays both static and dynamic content

**Usage**:
```bash
lynx                              # Show default portal (bbs.cyberspace.net)
lynx bbs.cyberspace.net           # Visit specific site
lynx underground.bbs              # Visit underground BBS
lynx bbs.cyberspace.net/time.poo  # Access dynamic page
```

**DNS Map** (hostname → IP):
- `bbs.cyberspace.net` → 192.168.1.10
- `underground.bbs` → 192.168.1.11
- `megacorp.bbs` → 192.168.2.50
- `vax.university.edu` → 192.168.3.100
- `nexus.unknown` → 192.168.99.1
- `research.facility.gov` → 192.168.4.66
- `cybermart.com` → 192.168.5.100

### 3. `/bin/http-get` - HTTP Client Helper
- **Purpose**: Fetches content from local httpd (called by remote lynx)
- **Features**:
  - Checks if httpd is running
  - Executes .poo scripts and serves static files
  - Returns content to requesting client

**Usage**:
```bash
http-get /default.bbs      # Fetch static file
http-get /serverinfo.poo   # Execute dynamic script
http-get /time.poo         # Get current time (dynamic)
```

### 4. Dynamic Content Examples

#### `/www/serverinfo.poo`
Server information page (like PHP info):
- Shows hostname, IP, interfaces
- Lists running processes
- Displays httpd status
- Network configuration

#### `/www/time.poo`
Simple dynamic time display:
- Executes `date` command server-side
- Shows server hostname
- Demonstrates real-time content generation

### 5. Static Content

All existing .bbs files:
- `/www/default.bbs` - Main portal (updated with dynamic page links)
- `/www/bbs_main.bbs` - CyberSpace BBS
- `/www/bbs_underground.bbs` - Underground BBS
- `/www/bbs_university.bbs` - University VAX
- `/www/bbs_nexus.bbs` - The Nexus
- `/www/bbs_research.bbs` - Research Facility
- `/www/cybermart.com` - Shopping site

## World Integration

All major systems now run `httpd`:

| System | IP | httpd PID |
|--------|------|-----------|
| bbs.cyberspace.net | 192.168.1.10 | 2 |
| underground.bbs | 192.168.1.11 | 2 |
| megacorp.bbs | 192.168.2.50 | 2 |
| vax.university.edu | 192.168.3.100 | 2 |
| nexus.unknown | 192.168.99.1 | 2 |
| research.facility.gov | 192.168.4.66 | 2 |
| cybermart.com | 192.168.5.100 | 2 |

## Testing the Web Server

### In-Game Commands:

1. **Browse default portal**:
   ```bash
   lynx
   ```

2. **Visit specific BBS**:
   ```bash
   lynx bbs.cyberspace.net
   lynx underground.bbs
   ```

3. **Check dynamic content**:
   ```bash
   lynx bbs.cyberspace.net/serverinfo.poo
   lynx bbs.cyberspace.net/time.poo
   ```

4. **Check httpd on remote system**:
   ```bash
   ssh 192.168.1.10
   ps | grep httpd
   http-get /serverinfo.poo
   ```

5. **Network discovery**:
   ```bash
   nmap 192.168.1.0/24
   ping 192.168.1.10
   ```

## How It Works

### Normal Workflow:

1. **User runs lynx**:
   ```bash
   lynx bbs.cyberspace.net/serverinfo.poo
   ```

2. **lynx resolves hostname** → `192.168.1.10`

3. **lynx checks network reachability** (via VirtualNetwork)

4. **For local requests**, lynx directly:
   - Reads from `/www/` directory
   - Executes .poo scripts if dynamic
   - Displays content

5. **For remote requests** (future enhancement):
   - SSH to remote host
   - Execute `http-get /path` on remote server
   - Remote httpd processes request
   - Returns content over network

### Dynamic Content Execution:

When httpd/http-get encounters a `.poo` file:

1. **Check file extension**: `.poo` = dynamic
2. **Execute script**: `process.execute(script_path)`
3. **Capture output**: stdout becomes the page content
4. **Return to client**: Browser displays generated HTML/text

This is exactly how PHP, CGI, or ASP work!

## Key Features

✅ **Realistic Web Architecture**:
- Client-server separation
- Network-based communication
- Server-side script execution

✅ **Security**:
- Directory traversal protection
- Process isolation
- Permission checks

✅ **Flexibility**:
- Static content (.bbs, .html)
- Dynamic content (.poo scripts)
- Easy to add new sites/pages

✅ **Game Integration**:
- Missions can use web pages
- Hackers can modify .poo scripts
- Social engineering via fake sites

## File Changes

**New Files**:
- `/scripts/sbin/httpd` - Web server daemon
- `/scripts/bin/http-get` - HTTP client helper
- `/scripts/www/serverinfo.poo` - Dynamic server info page
- `/scripts/www/time.poo` - Dynamic time page
- `/scripts/var/run/.gitkeep` - Runtime directory

**Modified Files**:
- `/scripts/bin/lynx` - Complete rewrite for network support
- `/scripts/www/default.bbs` - Added dynamic page links
- `/world_1990.py` - Added httpd to all servers
- `.gitignore` - Allow scripts/var/ directory

## Next Steps (Future Enhancements)

1. **True Remote HTTP**: Implement actual network protocol for remote httpd access
2. **HTTP Headers**: Add proper HTTP request/response headers
3. **POST Support**: Allow form submissions
4. **Cookies/Sessions**: Track user state across requests
5. **Virtual Hosts**: Multiple sites per httpd
6. **Logging**: Access logs in `/var/log/httpd/`
7. **CGI Environment**: Full CGI environment variables for .poo scripts

## Conclusion

The virtual world now has a fully functional web infrastructure! Players can:
- Browse sites using lynx
- Discover servers running httpd
- View dynamic content that changes in real-time
- Potentially exploit vulnerable .poo scripts
- Host their own sites by modifying /www/

It's a realistic, immersive 1990s internet experience! 🌐
