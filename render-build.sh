#!/usr/bin/env bash
# Render Build Script - Installs Chrome for Selenium

set -e

echo "🔧 Installing Python dependencies..."
pip install -r requirements.txt

echo "🌐 Installing Chrome using apt buildpack approach..."

# Create directories
mkdir -p /opt/render/project/.chrome
cd /opt/render/project/.chrome

# Download and extract Chrome
echo "Downloading Chrome..."
wget -q -O chrome-linux.zip https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/linux64/chrome-linux64.zip
unzip -q chrome-linux.zip
rm chrome-linux.zip

# Download and extract ChromeDriver
echo "Downloading ChromeDriver..."
wget -q -O chromedriver-linux.zip https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/linux64/chromedriver-linux64.zip
unzip -q chromedriver-linux.zip
rm chromedriver-linux.zip

# Set permissions
chmod +x chrome-linux64/chrome
chmod +x chromedriver-linux64/chromedriver

# Export paths
export CHROME_BIN=/opt/render/project/.chrome/chrome-linux64/chrome
export CHROMEDRIVER_PATH=/opt/render/project/.chrome/chromedriver-linux64/chromedriver

echo "✅ Chrome installed at: $CHROME_BIN"
echo "✅ ChromeDriver installed at: $CHROMEDRIVER_PATH"

# Verify
ls -la /opt/render/project/.chrome/chrome-linux64/
ls -la /opt/render/project/.chrome/chromedriver-linux64/

echo "🎉 Build complete!"
