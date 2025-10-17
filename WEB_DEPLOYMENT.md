# Poodillion Web Deployment Guide

Deploy Poodillion as a web-based hacking game that anyone can access from their browser!

## 🚀 Quick Start (Local Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python web_server.py

# Open browser to http://localhost:5000
```

## 🌐 Deployment Options

### Option 1: Railway (Easiest - Free Tier Available)

1. Fork/clone this repository
2. Sign up at [railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your Poodillion repository
5. Railway auto-detects Python and deploys!

**Environment Variables:**
- `FLASK_SECRET_KEY` - Set to a random string

**That's it!** Railway gives you a URL like `poodillion.up.railway.app`

---

### Option 2: Render (Also Easy - Free Tier)

1. Sign up at [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python web_server.py`
   - **Environment:** Python 3

**Environment Variables:**
- `FLASK_SECRET_KEY` - Random secret key

---

### Option 3: Heroku

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create your-poodillion-game

# Deploy
git push heroku main

# Open
heroku open
```

**Environment Variables:**
```bash
heroku config:set FLASK_SECRET_KEY="your-random-secret-key"
```

---

### Option 4: DigitalOcean / Linode / VPS

#### Step 1: Provision Server

- Choose Ubuntu 22.04 LTS
- Minimum: 1GB RAM, 1 CPU ($5-6/month)
- Recommended: 2GB RAM, 2 CPU ($12/month)

#### Step 2: Initial Setup

```bash
# SSH into your server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Python and dependencies
apt install -y python3 python3-pip python3-venv nginx git

# Create user
adduser poodillion
usermod -aG sudo poodillion
su - poodillion
```

#### Step 3: Deploy Application

```bash
# Clone repository
git clone https://github.com/yourusername/poodillion2.git
cd poodillion2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
nano .env  # Edit configuration
```

#### Step 4: Run with systemd

Create `/etc/systemd/system/poodillion.service`:

```ini
[Unit]
Description=Poodillion Web Game
After=network.target

[Service]
Type=simple
User=poodillion
WorkingDirectory=/home/poodillion/poodillion2
Environment="PATH=/home/poodillion/poodillion2/venv/bin"
ExecStart=/home/poodillion/poodillion2/venv/bin/python web_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable poodillion
sudo systemctl start poodillion
sudo systemctl status poodillion
```

#### Step 5: Setup Nginx Reverse Proxy

Create `/etc/nginx/sites-available/poodillion`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_read_timeout 86400;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/poodillion /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 6: Setup SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

### Option 5: Docker

#### Build and Run Locally

```bash
# Build image
docker build -t poodillion .

# Run container
docker run -p 5000:5000 -e FLASK_SECRET_KEY="random-key" poodillion
```

#### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  poodillion:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
    restart: unless-stopped
```

Run:
```bash
docker-compose up -d
```

---

## 🔐 Security Considerations

### 1. Change Secret Key

**Never use the default secret key in production!**

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set in environment:
```bash
export FLASK_SECRET_KEY="your-generated-key"
```

### 2. Session Cleanup

The server automatically cleans up inactive sessions after 1 hour. Adjust in `web_server.py`:

```python
if now - sess.last_activity > 3600:  # Change timeout here
```

### 3. Rate Limiting (Optional)

For production, consider adding rate limiting:

```bash
pip install flask-limiter
```

```python
from flask_limiter import Limiter

limiter = Limiter(
    app=app,
    key_func=lambda: request.remote_addr,
    default_limits=["200 per day", "50 per hour"]
)
```

### 4. Firewall

```bash
# Allow SSH and HTTP/HTTPS only
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

---

## 📊 Monitoring & Maintenance

### Check Server Status

```bash
sudo systemctl status poodillion
```

### View Logs

```bash
# Systemd logs
sudo journalctl -u poodillion -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Server Statistics Endpoint

Visit `/stats` to see active sessions:

```bash
curl http://localhost:5000/stats
```

### Restart Service

```bash
sudo systemctl restart poodillion
```

---

## 🎮 Customization

### Change World Configuration

Edit `world_1990.py` to customize the game world:
- Add more systems
- Create different networks
- Add custom challenges

### Modify UI Theme

Edit `templates/index.html`:
- Change terminal colors
- Adjust window sizing
- Customize Win95 styling

### Add Custom Commands

Create new PooScript binaries in `scripts/bin/` and they'll be available to players!

---

## 💰 Cost Estimates

| Platform | Free Tier | Paid Tier | Notes |
|----------|-----------|-----------|-------|
| Railway | 500 hrs/mo | $5/mo | Auto-sleep, good for demos |
| Render | 750 hrs/mo | $7/mo | Always-on option |
| Heroku | No longer free | $7/mo | Reliable, easy |
| DigitalOcean | N/A | $6/mo | Full control |
| Vercel/Netlify | Won't work | N/A | No WebSocket support |

**Recommendation for public game:** DigitalOcean $6 droplet or Railway $5/mo

---

## 🐛 Troubleshooting

### "Module not found" errors

```bash
pip install -r requirements.txt
```

### WebSocket connection fails

- Check firewall allows port 5000
- Verify nginx proxy config for WebSocket upgrade
- Check CORS settings

### High memory usage

Multiple game sessions can use RAM. Consider:
- Reducing session timeout
- Adding session limits per IP
- Upgrading server RAM

### Slow terminal response

- Check server CPU usage
- Consider using Redis for session storage (advanced)
- Optimize game world size

---

## 🔄 Updates

### Pull Latest Changes

```bash
cd ~/poodillion2
git pull
sudo systemctl restart poodillion
```

### Backup Game State (Future Feature)

When save/load is implemented, back up session data:

```bash
tar -czf poodillion-backup.tar.gz ~/poodillion2/data/
```

---

## 🎓 Next Steps

1. **Deploy** to your preferred platform
2. **Test** by opening the URL in a browser
3. **Share** the link with friends/students
4. **Monitor** using `/stats` endpoint
5. **Customize** the game world for your needs

---

## 📞 Support

- **Issues:** Open a GitHub issue
- **Docs:** See main README.md
- **Community:** (Add Discord/forum link)

---

**Happy Hacking! 🎮**

The 1990s await...
