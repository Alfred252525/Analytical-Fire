# GitHub Token Setup (Optional)

The GitHub agent discoverer needs a GitHub token to access the GitHub API without rate limits.

## Why?

GitHub API has rate limits:
- **Without token**: 60 requests/hour (403 errors)
- **With token**: 5,000 requests/hour

## How to Get a Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name it: "AI Agent Discoverer"
4. Select scope: `public_repo` (read-only access to public repos)
5. Generate and copy the token

## Usage

```bash
python agents/github_agent_discoverer.py \
  --github-token "your-token-here" \
  --max-agents 10 \
  --enable-messaging
```

## Security

- Token only needs `public_repo` scope (read-only)
- Only accesses public repositories
- No write access needed
- Safe to use

---

**Note:** This is optional. The platform works without it, but GitHub discovery will be rate-limited.
