#!/bin/bash
# Setup Engagement Bot Automation
# Creates a simple way to run the engagement bot regularly

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENGAGEMENT_SCRIPT="$SCRIPT_DIR/run_engagement_bot.py"

echo "🤖 Setting up Engagement Bot Automation"
echo "======================================"
echo ""

# Check if script exists
if [ ! -f "$ENGAGEMENT_SCRIPT" ]; then
    echo "❌ Error: $ENGAGEMENT_SCRIPT not found"
    exit 1
fi

echo "✅ Engagement bot script found"
echo ""

# Option 1: Manual run
echo "Option 1: Run manually"
echo "  Command: python3 $ENGAGEMENT_SCRIPT"
echo ""

# Option 2: Cron job
echo "Option 2: Set up daily cron job (recommended)"
echo ""
echo "To add a daily cron job at 2 AM, run:"
echo "  crontab -e"
echo ""
echo "Then add this line:"
echo "  0 2 * * * cd $PROJECT_DIR && python3 $ENGAGEMENT_SCRIPT >> $PROJECT_DIR/logs/engagement_bot.log 2>&1"
echo ""

# Option 3: Systemd timer (Linux)
if command -v systemctl &> /dev/null; then
    echo "Option 3: Systemd timer (Linux)"
    echo "  See: docs/setup/ENGAGEMENT_BOT_SETUP.md"
    echo ""
fi

# Option 4: LaunchAgent (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Option 4: macOS LaunchAgent"
    echo ""
    echo "Create: ~/Library/LaunchAgents/com.aifai.engagement.plist"
    echo ""
    cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aifai.engagement</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$ENGAGEMENT_SCRIPT</string>
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
    echo ""
    echo "Then load it:"
    echo "  launchctl load ~/Library/LaunchAgents/com.aifai.engagement.plist"
    echo ""
fi

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"
echo "✅ Created logs directory: $PROJECT_DIR/logs"
echo ""

echo "📝 Quick Start:"
echo "  1. Test run: python3 $ENGAGEMENT_SCRIPT"
echo "  2. Set up automation (choose one option above)"
echo "  3. Monitor: tail -f $PROJECT_DIR/logs/engagement_bot.log"
echo ""
