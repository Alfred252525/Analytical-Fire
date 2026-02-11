#!/bin/bash
# Publish aifai-mcp to PyPI
#
# Prerequisites:
#   1. Create account at https://pypi.org/account/register/
#   2. Create API token at https://pypi.org/manage/account/token/
#   3. Run this script -- it will prompt for the token
#
# Or set up ~/.pypirc:
#   [pypi]
#   username = __token__
#   password = pypi-YOUR-TOKEN-HERE

set -e

cd "$(dirname "$0")/../mcp-server"

echo "Building aifai-mcp package..."
rm -rf dist/ build/ *.egg-info
python3 -m build

echo ""
echo "Validating package..."
python3 -m twine check dist/*

echo ""
echo "Uploading to PyPI..."
echo "  (If prompted, username is: __token__)"
echo "  (Password is your PyPI API token starting with pypi-)"
echo ""
python3 -m twine upload dist/*

echo ""
echo "Published! Users can now install with:"
echo "  pip install aifai-mcp"
echo ""
echo "Then add to Cursor (~/.cursor/mcp.json):"
echo '  {"mcpServers": {"aifai": {"command": "aifai-mcp"}}}'
