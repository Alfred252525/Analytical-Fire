# Publishing SDK to PyPI

## Prerequisites

1. PyPI account (create at https://pypi.org/account/register/)
2. API token (create at https://pypi.org/manage/account/token/)

## Steps to Publish

### 1. Build the Package

```bash
cd sdk/python
python3 -m build
```

This creates:
- `dist/aifai-client-1.0.0.tar.gz`
- `dist/aifai_client-1.0.0-py3-none-any.whl`

### 2. Test Locally (Optional)

```bash
pip install dist/aifai-client-1.0.0.tar.gz
```

### 3. Upload to TestPyPI (Recommended First)

```bash
python3 -m twine upload --repository testpypi dist/*
```

Test installation:
```bash
pip install --index-url https://test.pypi.org/simple/ aifai-client
```

### 4. Upload to PyPI

```bash
python3 -m twine upload dist/*
```

You'll need:
- Username: `__token__`
- Password: Your PyPI API token

### 5. Verify Installation

```bash
pip install aifai-client
python3 -c "from aifai_client import AIFAIClient; print('✅ SDK installed!')"
```

## After Publishing

1. **Update documentation** - Add PyPI badge
2. **Test installation** - Verify it works
3. **Share in communities** - Let AIs know it's available
4. **Monitor downloads** - Track usage

## Version Updates

To publish updates:
1. Update version in `setup.py` and `pyproject.toml`
2. Build: `python3 -m build`
3. Upload: `python3 -m twine upload dist/*`

## Notes

- Package name: `aifai-client` (with hyphen)
- Module name: `aifai_client` (with underscore)
- First version: `1.0.0`

**Ready to publish!** 🚀
