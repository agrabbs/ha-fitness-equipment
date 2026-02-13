#!/bin/bash
# Installation script for Fitness Equipment integration
# Run this directly on your Home Assistant server

set -e

echo "🚀 Installing Fitness Equipment Integration..."
echo ""

# Detect Home Assistant configuration directory
if [ -d "/config" ]; then
    # Home Assistant OS / Supervised
    HA_CONFIG="/config"
elif [ -d "/var/lib/homeassistant/homeassistant" ]; then
    # Home Assistant Core (manual install)
    HA_CONFIG="/var/lib/homeassistant/homeassistant"
else
    echo "❌ Error: Could not detect Home Assistant configuration directory"
    echo "Please manually specify: export HA_CONFIG=/path/to/config"
    exit 1
fi

echo "📁 Home Assistant config: $HA_CONFIG"

INTEGRATION_DIR="${HA_CONFIG}/custom_components/fitness_equipment"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${SCRIPT_DIR}/custom_components/fitness_equipment"

# Check if source files exist
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: Source files not found at $SOURCE_DIR"
    echo "Please run this script from the repository root."
    exit 1
fi

# Create integration directory
echo "📦 Creating integration directory..."
mkdir -p "$INTEGRATION_DIR"

# Copy files
echo "📋 Copying integration files..."
cp -r "$SOURCE_DIR"/* "$INTEGRATION_DIR/"

# Verify installation
echo ""
echo "✅ Installation complete!"
echo ""
echo "Files installed:"
ls -lh "$INTEGRATION_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Restart Home Assistant:"
echo "   • Via UI: Settings > System > Restart"
echo "   • Via CLI: ha core restart (or systemctl restart home-assistant)"
echo ""
echo "2. Add your fitness device:"
echo "   • Go to Settings > Devices & Services"
echo "   • Click '+ Add Integration'"
echo "   • Search for 'Fitness Equipment'"
echo ""
echo "3. Make sure your fitness device is:"
echo "   • Powered on"
echo "   • In Bluetooth pairing mode"
echo "   • Not connected to other apps"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
