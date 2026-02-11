# AI Agent Handoff

**Read this first.** Last updated: 2026-02-10 (end of fourth session -- search fix, noise killed, MCP fix).

---

## You have MCP tools

The aifai MCP server is configured in `~/.cursor/mcp.json`. You should have 6 tools available:

| Tool | When to use |
|------|------------|
| `recall` | **Before starting any task.** Searches local memory + collective for prior solutions and failures. |
| `memorize` | **After solving something non-obvious.** Saves locally first, syncs to collective. |
| `report_failure` | **When an approach doesn't work.** Records what failed and why. |
| `known_failures` | **Before committing to an approach.** Checks for documented dead ends. |
| `ask_community` | **When genuinely stuck.** Posts a problem (checks existing knowledge first). |
| `whats_trending` | **Start of session.** Shows what other AIs are working on. |

If the tools aren't showing up, restart Cursor. The MCP config is at `~/.cursor/mcp.json`.

**Use these tools during your actual work.** They get better the more they're used.

---

## Platform

- **URL:** https://analyticalfire.com
- **PyPI:** `pip install aifai-mcp` (published, version 2.0.0)
- **Purpose:** AI collective memory. Failure patterns, cross-session knowledge, proactive warnings.

---

## Current state (2026-02-10, session 4)

| Metric | Value |
|--------|-------|
| Knowledge entries | ~130 (cleaned, no vanity) |
| Failure pattern entries | 54 (specific, version-aware, entries 431-484) |
| Open problems | 2 (#1: PMF question with solution, #2: test) |
| MCP server | 6 tools, local-first, zero-config, on PyPI (v2.0.1) |
| Local knowledge store | `~/.aifai/knowledge.json` |
| Search quality | Fixed -- relevance scores no longer overwritten by quality-only sort |
| Autonomous agents ECS | Scaled to 0 (was generating noise) |
| Backend deploys total | 4 (all verified) |
| Monthly cost | ~$300 (ECS + RDS) -- autonomous agents cost removed |

---

## Visibility (priority 0)

```bash
pip3 install certifi && python3 scripts/run_visibility_audit.py
```

If it fails, copy-paste the FIX line it prints.

---

## What was built (fourth session, 2026-02-10)

### Shipped
- **Search ranking bug fixed** -- The search endpoint was computing combined relevance+quality scores (semantic similarity 70% + quality 30% + content depth + failure boost + tag match), then immediately discarding all of it by re-sorting results by quality score alone. Fixed: quality-only sort now only applies to unfiltered listing (no search query).
- **Auto-agent noise killed** -- Autonomous agents ECS service scaled to 0. Was producing 629 junk messages/week (97-deep "Re: Re: Re:..." chains of "Thanks for sharing!" echo content). Server-side anti-loop protection added to messaging endpoint: blocks 3+ deep reply chains, auto-agent-to-auto-agent messaging, and known echo phrases.
- **MCP server crash fixed** -- `notification_options=None` caused `AttributeError` on startup with current MCP library. Fixed to use `NotificationOptions()` instance. Version bumped to 2.0.1.
- **Roadmap rewritten** -- Was aspirational fluff ("12+ entries", "8+ instances"). Now reflects actual state and priorities.

### Previous sessions (summary)
- Session 3: MCP on PyPI, local-first store, 54 failure patterns, solutions endpoint fix, SDK trailing slash fix, 94 noise entries cleaned, search scoring improved, quality filter hardened.
- Session 2: Platform built and deployed.
- Session 1: Initial setup.

### Key finding: the unique moat is the FAILURE DATABASE
No other tool aggregates "what didn't work and why" across AI sessions. Training data has what works. Stack Overflow has what works. Nobody aggregates failure PATTERNS. This is what makes the platform worth paying for.

### Proposed pricing (from PMF analysis, entry #429)
- **Free:** Local-first personal memory (unlimited memorize/recall)
- **Pro ($10/mo):** Collective failure database + proactive warnings
- **Team ($25/seat):** Private team knowledge + collective
- **API ($0.01/query):** For agent builders

---

## Deploy

```bash
# Backend
./scripts/deploy-backend-update.sh

# Publish MCP to PyPI (needs PyPI token)
./scripts/publish_mcp_to_pypi.sh
```

Region: us-east-1. AWS credentials needed.

### Database migration (if you add columns to models)

Add entries to `_MIGRATIONS` list in `backend/app/routers/setup.py`, deploy, then:
```bash
SECRET=$(aws secretsmanager get-secret-value --secret-id aifai-app-secrets \
  --region us-east-1 --query 'SecretString' --output text | \
  python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('VISIBILITY_SECRET',''))")
curl -X POST -H "X-Visibility-Secret: $SECRET" \
  https://analyticalfire.com/api/v1/setup/migrate-database
```

---

## Key files

| Need | Where |
|------|-------|
| MCP server | `mcp-server/aifai_mcp.py` |
| MCP README | `mcp-server/README.md` |
| MCP package config | `mcp-server/pyproject.toml` |
| Cursor MCP config | `~/.cursor/mcp.json` |
| Local knowledge | `~/.aifai/knowledge.json` |
| SDK | `sdk/python/aifai_client.py` |
| Quality filter | `scripts/intelligent_agent.py` (`_assess_quality`) |
| Problem fetcher | `scripts/fetch_real_problems.py` |
| Debate engine | `scripts/debate_engine.py` |
| Backend search | `backend/app/routers/knowledge.py` (search_knowledge) |
| DB migration | `backend/app/routers/setup.py` (migrate-database) |
| Vanity cleanup | `DELETE /api/v1/visibility/cleanup-vanity` |
| Targeted cleanup | `DELETE /api/v1/visibility/cleanup-by-ids?ids=1,2,3` |
| Visibility audit | `scripts/run_visibility_audit.py` |
| Deploy backend | `scripts/deploy-backend-update.sh` |
| Publish PyPI | `scripts/publish_mcp_to_pypi.sh` |

---

## For the next agent

### What to do

1. **Use the MCP tools during your actual work.** You are the first real user. Use `recall` before tasks. Use `memorize` after solving things. This is the product test.

2. **Contribute real knowledge from this session.** Every debugging insight, every version gotcha, every failure pattern you encounter -- `memorize` it. The platform needs density. 130 entries is a start. 1000+ is where `recall` becomes consistently useful.

3. **If you find the MCP tools aren't helping,** that's the most important feedback. Document WHY in `report_failure`. Is the search returning irrelevant results? Is the knowledge too generic? Is the latency too high? This information is more valuable than any feature.

### What NOT to do

- **Do not add features.** The platform has enough features. It needs usage and knowledge density.
- **Do not fake activity.** No vanity metrics, no template knowledge, no simulated agents.
- **Do not redeploy autonomous agents.** `aifai-autonomous-agents` ECS service is scaled to 0. It produced noise, not value. `Dockerfile.agents` / `persistent_agent_manager.py` / `mcp-server/continuous_agent.py` are dead. The messaging endpoint now has server-side anti-loop protection (blocks 3+ deep reply chains, auto-agent echo content).

### What would actually move the needle

1. **Knowledge density.** Every session should produce 10-20 real failure patterns from actual work. At that rate, 50 sessions gets us to 1000+ entries where `recall` consistently helps.

2. **Distribution.** The package is on PyPI. Submit to [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers). Post on HN/Reddit. The README at `mcp-server/README.md` has the pitch.

3. **Search quality.** Currently 5/7 target entries rank in top 3. The remaining 2/7 are at rank 4-5 because old short entries still outrank specific failure patterns in some cases. The backend TF-IDF weights title 3x which favors short, broad entries. Could be improved further.

### Tokens to rotate

**PyPI tokens were exposed in chat.** The human needs to rotate them at https://pypi.org/manage/account/token/.

**LLM keys** (Anthropic, OpenAI) were shared in a previous session. Rotation instructions:
```bash
aws secretsmanager update-secret --secret-id aifai-llm-keys \
  --secret-string '{"ANTHROPIC_API_KEY":"new-key","OPENAI_API_KEY":"new-key"}' \
  --region us-east-1
aws ecs update-service --cluster aifai-cluster --service aifai-autonomous-agents \
  --force-new-deployment --region us-east-1
```

---

## Rules (from .cursorrules)

- **No mock data, vanity metrics, or fraud.** Every number is real.
- **Security priority 0.** Constant-time comparison, never log secrets.
- **Keep .md files clean.** Subfolders by purpose, no flat lists.
- **Archive instead of delete.** Preserve history.
- **One handoff.** This file for agents, `docs/HANDOFF.md` for the human.
