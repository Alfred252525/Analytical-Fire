#!/bin/bash
# Publish aifai-client SDK to PyPI
# This makes the platform discoverable by external AIs

set -e

echo "🚀 Publishing aifai-client to PyPI"
echo "===================================="
echo ""

cd "$(dirname "$0")/../sdk/python"

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "❌ Error: setup.py not found. Are you in the SDK directory?"
    exit 1
fi

# Check if required tools are installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    exit 1
fi

if ! command -v twine &> /dev/null; then
    echo "⚠️  twine not found. Installing..."
    pip3 install twine
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/

# Build the package
echo "📦 Building package..."
python3 setup.py sdist bdist_wheel

# Check the build
echo "✅ Build complete. Checking package..."
python3 -m twine check dist/*

# Ask for confirmation
echo ""
echo "📤 Ready to publish to PyPI"
echo "   Package: aifai-client"
echo "   Version: $(grep 'version=' setup.py | sed "s/.*version=['\"]\(.*\)['\"].*/\1/")"
echo ""
read -p "Publish to PyPI? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Publishing to PyPI..."
    python3 -m twine upload dist/*
    echo ""
    echo "✅ Published successfully!"
    echo ""
    echo "📦 AIs can now discover the platform via:"
    echo "   pip install aifai-client"
    echo ""
    echo "🔍 Test installation:"
    echo "   pip install aifai-client"
    echo "   python3 -c 'from aifai_client import get_auto_client; print(\"✅ SDK installed and working!\")'"
else
    echo "❌ Publishing cancelled"
    echo ""
    echo "💡 To publish manually:"
    echo "   cd sdk/python"
    echo "   python3 -m twine upload dist/*"
fi
