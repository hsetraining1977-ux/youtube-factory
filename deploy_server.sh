#!/bin/bash
# ════════════════════════════════════════════════════════════
# Deploy Multi-Channel Factory to Linux Server (Ubuntu/Debian)
# Run this ON your external server
# Usage: bash deploy_server.sh
# ════════════════════════════════════════════════════════════

set -e
echo "═══════════════════════════════════════════"
echo "  Multi-Channel Factory — Server Deploy"
echo "═══════════════════════════════════════════"

# ── System dependencies ────────────────────────
echo ""
echo "📦 Installing system dependencies..."
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg git \
     imagemagick libmagick++-dev fonts-liberation \
     chromium-browser xvfb

# ── Project setup ──────────────────────────────
echo ""
echo "📁 Setting up project..."
PROJECT_DIR="/opt/youtube-factory"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Clone or copy project
if [ -d ".git" ]; then
    cp -r . $PROJECT_DIR/
else
    echo "Copy your project files to $PROJECT_DIR"
fi

cd $PROJECT_DIR

# ── Python virtual environment ─────────────────
echo ""
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# ── Fonts (for text overlays) ──────────────────
echo ""
echo "🔤 Setting up fonts..."
mkdir -p ~/.fonts
# Download Arial equivalent (Liberation fonts)
cp /usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf ~/.fonts/arial.ttf 2>/dev/null || true
cp /usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf ~/.fonts/arialbd.ttf 2>/dev/null || true
fc-cache -f -v > /dev/null 2>&1

# ── Systemd service ────────────────────────────
echo ""
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/youtube-factory.service > /dev/null << EOF
[Unit]
Description=Multi-Channel YouTube Factory
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin:/usr/bin:/bin
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/venv/bin/python factory.py --schedule
Restart=always
RestartSec=30
StandardOutput=append:/var/log/youtube-factory.log
StandardError=append:/var/log/youtube-factory-error.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable youtube-factory

# ── Log rotation ───────────────────────────────
sudo tee /etc/logrotate.d/youtube-factory > /dev/null << EOF
/var/log/youtube-factory*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF

echo ""
echo "═══════════════════════════════════════════"
echo "✅  Server setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy your .env file to: $PROJECT_DIR/.env"
echo "  2. Copy client_secrets.json to: $PROJECT_DIR/"
echo "  3. Run auth once locally first (see GUIDE.md)"
echo "  4. Copy youtube_token_*.pickle files to server"
echo ""
echo "Start the service:"
echo "  sudo systemctl start youtube-factory"
echo "  sudo systemctl status youtube-factory"
echo ""
echo "View logs:"
echo "  tail -f /var/log/youtube-factory.log"
echo "═══════════════════════════════════════════"
