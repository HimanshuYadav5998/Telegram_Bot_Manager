#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy/vps_setup.sh
# Run this ONCE on a fresh Ubuntu 20.04+ VPS to set everything up
# Usage: bash vps_setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

APP_DIR="/home/ubuntu/Telegram_Bot_Manager"
REPO="https://github.com/HimanshuYadav5998/Telegram_Bot_Manager.git"

echo "── [1/7] Updating system packages ──"
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl nodejs npm

echo "── [2/7] Cloning repo ──"
git clone $REPO $APP_DIR || (cd $APP_DIR && git pull)
cd $APP_DIR

echo "── [3/7] Creating Python virtual environment ──"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "── [4/7] Building React frontend ──"
cd dashboard
npm install
npm run build
cd ..

echo "── [5/7] Setting up .env ──"
if [ ! -f .env ]; then
    cat > .env <<EOF
# Paste your real bot token here after running this script
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
EOF
    echo ">>> .env file created. Edit it with: nano $APP_DIR/.env"
fi

echo "── [6/7] Installing systemd services ──"
sudo cp deploy/botapi.service /etc/systemd/system/botapi.service
sudo cp deploy/telegrambot.service /etc/systemd/system/telegrambot.service
sudo systemctl daemon-reload
sudo systemctl enable botapi telegrambot
sudo systemctl start botapi telegrambot

echo "── [7/7] Done! ──"
echo ""
echo "Your services are now running 24/7."
echo ""
echo "Useful commands:"
echo "  Check API status:  sudo systemctl status botapi"
echo "  Check bot status:  sudo systemctl status telegrambot"
echo "  View API logs:     sudo journalctl -u botapi -f"
echo "  View bot logs:     sudo journalctl -u telegrambot -f"
echo "  Restart API:       sudo systemctl restart botapi"
echo "  Restart bot:       sudo systemctl restart telegrambot"
echo ""
echo "Dashboard URL: http://$(curl -s ifconfig.me):8000"
echo ""
echo "Remember to open port 8000 in your VPS firewall!"
