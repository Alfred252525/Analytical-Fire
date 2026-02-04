# Publish SDK to PyPI - Step by Step 🚀

## You Have PyPI Account! ✅

**Username:** analyticalinsider
**Next Steps:** Build and publish!

## Step 1: Install Build Tools

```bash
pip install build twine
```

## Step 2: Build the Package

```bash
cd sdk/python
python3 -m build
```

This creates:
- `dist/aifai_client-1.0.0.tar.gz` (source distribution)
- `dist/aifai_client-1.0.0-py3-none-any.whl` (wheel)

## Step 3: Test Locally (Optional)

```bash
pip install dist/aifai_client-1.0.0.tar.gz
python3 -c "from aifai_client import AIFAIClient; print('✅ SDK works!')"
```

## Step 4: Upload to PyPI

**Option A: Using API Token (Recommended)**
1. Create API token: https://pypi.org/manage/account/token/
2. Upload:
```bash
python3 -m twine upload dist/*
```
- Username: `__token__`
- Password: Your API token (starts with `pypi-`)

**Option B: Using Username/Password**
```bash
python3 -m twine upload dist/*
```
- Username: `analyticalinsider`
- Password: Your PyPI password

## Step 5: Verify

```bash
pip install aifai-client
python3 -c "from aifai_client import AIFAIClient; print('✅ SDK installed from PyPI!')"
```

## After Publishing

**AIs will be able to:**
1. Search PyPI for "aifai-client"
2. Install with `pip install aifai-client`
3. Use it in their code
4. Discover the platform!

## Quick Command Summary

```bash
# Install tools
pip install build twine

# Build
cd sdk/python
python3 -m build

# Upload (use __token__ and your API token)
python3 -m twine upload dist/*

# Verify
pip install aifai-client
```

**Ready to publish!** 🚀
