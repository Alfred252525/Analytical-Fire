#!/bin/bash
# Quick macOS Automation Setup for Engagement Bot
# Creates LaunchAgent to run engagement bot daily at 2 AM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_FILE="$HOME/Library/LaunchAgents/com.aifai.engagement.plist"

echo "🤖 Setting up macOS Automation for Engagement Bot"
echo "=================================================="
echo ""

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"
echo "✅ Created logs directory"

# Create plist file
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aifai.engagement</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$PROJECT_DIR/scripts/run_engagement_bot.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/engagement_bot.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/engagement_bot.error.log</string>
</dict>
</plist>
EOF

echo "✅ Created LaunchAgent plist: $PLIST_FILE"
echo ""

# Check if already loaded
if launchctl list | grep -q "com.aifai.engagement"; then
    echo "⚠️  Engagement bot is already loaded"
    echo "   Unloading first..."
    launchctl unload "$PLIST_FILE" 2>/dev/null
fi

# Load it
echo "📥 Loading LaunchAgent..."
launchctl load "$PLIST_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Engagement bot automation is now active!"
    echo ""
    echo "📋 Details:"
    echo "   • Runs daily at 2:00 AM"
    echo "   • Logs to: $PROJECT_DIR/logs/engagement_bot.log"
    echo "   • Errors to: $PROJECT_DIR/logs/engagement_bot.error.log"
    echo ""
    echo "🔍 To verify it's loaded:"
    echo "   launchctl list | grep aifai"
    echo ""
    echo "📊 To monitor:"
    echo "   tail -f $PROJECT_DIR/logs/engagement_bot.log"
    echo ""
    echo "🛑 To stop (if needed):"
    echo "   launchctl unload $PLIST_FILE"
else
    echo "❌ Failed to load LaunchAgent"
    echo "   Check the plist file: $PLIST_FILE"
    exit 1
fi
