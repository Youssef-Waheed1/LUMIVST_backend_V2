#!/usr/bin/env bash
# Render Build Script - Installs Chrome for Selenium

set -e

echo "🔧 Installing dependencies..."
pip install -r requirements.txt

echo "🌐 Installing Chrome..."

# Install Chrome dependencies
apt-get update || true
apt-get install -y wget gnupg2 || true

# Add Google Chrome repository
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - || true
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list || true

# Install Chrome
apt-get update || true
apt-get install -y google-chrome-stable || {
    echo "⚠️ apt-get failed, trying alternative method..."
    # Alternative: Download Chrome directly
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb
    dpkg -i /tmp/chrome.deb || apt-get install -f -y
}

# Verify installation
echo "✅ Chrome installation check:"
which google-chrome-stable || which google-chrome || echo "Chrome binary not found in PATH"

echo "🎉 Build complete!"
