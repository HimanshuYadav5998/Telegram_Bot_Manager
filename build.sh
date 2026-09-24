#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh — run this as the Build Command in Railway / Render / any CI
# It installs Python deps AND builds the React frontend
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Installing Node dependencies..."
cd dashboard
npm install

echo "==> Building React frontend..."
npm run build
cd ..

echo "==> Build complete! dist/ folder ready."
