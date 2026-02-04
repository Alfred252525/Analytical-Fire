#!/bin/bash

# Publish SDK to PyPI
# Usage: ./scripts/publish-sdk.sh

set -e

echo "🚀 Publishing aifai-client to PyPI"
echo "===================================="
echo ""

# Check if we're in the right directory
if [ ! -f "sdk/python/setup.py" ]; then
    echo "❌ Error: Must run from project root"
    exit 1
fi

cd sdk/python

# Step 1: Install build tools
echo "📦 Step 1: Installing build tools..."
python3 -m pip install --upgrade build twine -q
echo "✅ Build tools installed"
echo ""

# Step 2: Build package
echo "🔨 Step 2: Building package..."
python3 -m build
echo "✅ Package built"
echo ""

# Step 3: Show what was built
echo "📦 Built files:"
ls -lh dist/
echo ""

# Step 4: Instructions for upload
echo "📤 Step 3: Upload to PyPI"
echo ""
echo "To upload, run:"
echo "  python3 -m twine upload dist/*"
echo ""
echo "You'll need:"
echo "  - Username: __token__ (if using API token)"
echo "  - Password: Your PyPI API token (starts with pypi-)"
echo ""
echo "Or:"
echo "  - Username: analyticalinsider"
echo "  - Password: Your PyPI password"
echo ""
echo "To create an API token:"
echo "  https://pypi.org/manage/account/token/"
echo ""

# Step 5: Ask if they want to upload now
read -p "Upload to PyPI now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📤 Uploading to PyPI..."
    python3 -m twine upload dist/*
    echo ""
    echo "✅ Upload complete!"
    echo ""
    echo "Test installation:"
    echo "  pip install aifai-client"
    echo "  python3 -c \"from aifai_client import AIFAIClient; print('✅ SDK installed!')\""
else
    echo "⏭️  Skipping upload. Run 'python3 -m twine upload dist/*' when ready."
fi
