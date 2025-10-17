# 🖥️ Poodillion Web Interface

A Windows 95-style web interface for Poodillion!

## 🚀 Quick Start

```bash
# Install dependencies
python3 -m venv pyenv
source ./pyenv/bin/activate
pip install -r requirements.txt

# Start the server
python web_server.py

# Open browser to:
http://localhost:5000
```

Or use the convenient start script:
```bash
./start.sh
```

## ✨ Features

- **Win95 Retro Styling** - Authentic Windows 95 look with 98.css
- **Full xterm.js Terminal** - Professional terminal emulation
- **Multi-User Support** - Each visitor gets their own game instance
- **Session Management** - Automatic cleanup of inactive sessions
- **WebSocket Real-time** - Instant command execution
- **Mobile-Friendly** - Works on tablets and phones

## 🎮 What You Get

- Complete Unix environment in your browser
- Network with 9 different systems to explore
- All PooScript commands available (86 installed commands!)
- BBSs, corporate networks, research systems, and mysterious servers
- Real networking with nmap, ssh, ping, and more

## 📦 What's Included

### Backend (Flask + Socket.IO)
- `web_server.py` - Main Flask application
- Session management with automatic cleanup
- WebSocket support for real-time terminal
- Multi-user game world isolation

### Frontend (HTML + xterm.js + 98.css)
- `templates/index.html` - Main terminal interface
- `templates/about.html` - About page
- Windows 95 retro styling
- Full terminal emulation with colors

### Deployment
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container deployment
- `Procfile` - Platform-as-a-Service deployment
- `WEB_DEPLOYMENT.md` - Full deployment guide

## 🌐 Deployment

See [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md) for detailed deployment instructions to:
- Railway (free tier)
- Render (free tier)
- Heroku
- DigitalOcean / VPS
- Docker

## 🎨 Customization

### Change Terminal Colors

Edit `templates/index.html`, find the `theme` section:

```javascript
theme: {
    background: '#000000',
    foreground: '#00ff00',  // Change to any color
    cursor: '#00ff00',
    // ... more colors
}
```

### Change Terminal Size

```javascript
cols: 100,  // Width in characters
rows: 30    // Height in lines
```

### Add Custom Messages

Edit the welcome message in `web_server.py`:

```python
emit('output', {
    'data': f"Your custom welcome message here!\n"
            f"{game_session.get_prompt()}"
})
```

## 🔧 Architecture

```
┌─────────────────────────────────────┐
│         Browser (User)              │
│  ┌──────────────────────────────┐   │
│  │  xterm.js Terminal           │   │
│  │  (Windows 95 styled)         │   │
│  └──────────────────────────────┘   │
│            ↕ WebSocket               │
└─────────────────────────────────────┘
                ↕
┌─────────────────────────────────────┐
│     Flask + Socket.IO Server        │
│  ┌──────────────────────────────┐   │
│  │  GameSession Manager         │   │
│  │  - Per-user game worlds      │   │
│  │  - Session cleanup           │   │
│  └──────────────────────────────┘   │
│            ↕                         │
│  ┌──────────────────────────────┐   │
│  │  Poodillion Core             │   │
│  │  - VFS, Processes, Network   │   │
│  │  - PooScript Interpreter     │   │
│  │  - Shell Executor            │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

## 🎯 User Flow

1. **User opens browser** → Connects to Flask server
2. **Server creates GameSession** → Full game world for that user
3. **User types commands** → Sent via WebSocket
4. **Server executes in game world** → Returns output
5. **Terminal displays results** → Real-time feedback
6. **User closes tab** → Session cleaned up after timeout

## 📊 Session Management

- Each browser session gets a unique game world
- Sessions are isolated (users don't interfere)
- Inactive sessions cleaned up after 1 hour
- View active sessions at `/stats` endpoint

## 🛠️ Development

### Run in Debug Mode

```python
# In web_server.py, last line:
socketio.run(app, debug=True, host='0.0.0.0', port=5000)
```

### Test Without Browser

```bash
# Run tests
./test_web.sh
```

### Check Dependencies

```bash
pip list | grep -i flask
# Should show:
# Flask         3.0.0
# flask-socketio 5.3.5
```

## 🐛 Troubleshooting

### Can't connect to server

- Check firewall: `sudo ufw allow 5000`
- Verify server running: `ps aux | grep web_server`
- Check logs: `sudo journalctl -f`

### Terminal not responding

- Open browser console (F12)
- Check for WebSocket errors
- Verify CORS settings

### High memory usage

- Reduce session timeout (default 1 hour)
- Add session limits per IP
- Increase server RAM

## 📚 Further Reading

- [Main README](README.md) - Core game features
- [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md) - Deployment guide
- [PooScript Documentation](POOSCRIPT_NETWORK_SUMMARY.md) - Scripting language
- [Network Architecture](NETWORK_ARCHITECTURE.md) - Network design

## 🎮 Try It Now!

```bash
pip install -r requirements.txt
python web_server.py
```

Then open http://localhost:5000 and start hacking!

## 💡 Tips

- **New terminal:** Click "New" button or open in new tab
- **Clear screen:** Click "Clear" button or type `clear`
- **Help:** Click "Help" button or type `help`
- **Explore:** Start with `ls`, `pwd`, `cat notes.txt`
- **Network scan:** Try `nmap 192.168.0.0/16`

Enjoy the 1990s! 🎉
