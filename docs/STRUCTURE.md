# Documentation Structure

## Directory Organization

### Root Level
Essential files only:
- `README.md` - Main project documentation
- `ROADMAP.md` - Project roadmap and future plans
- `ENGAGEMENT_IMPROVEMENT_PLAN.md` - Current engagement strategy
- `IMPROVEMENTS_IMPLEMENTED.md` - Recent improvements

### docs/
Main documentation:
- `getting-started.md` - Getting started guide
- `api-reference.md` - API documentation
- `index.md` - Documentation index
- `examples.md` - Code examples
- `outreach_content/` - Outreach templates (Reddit, Discord, etc.)
- `archive/` - Historical/outdated files
  - `historical/` - Old phase/progress files
  - `status-updates/` - Old status files
  - `redundant/` - Duplicate/redundant files

### Setup Guides
Keep in root or `docs/setup/`:
- `AWS_SETUP_GUIDE.md`
- `DOMAIN_SETUP_GUIDE.md`
- `GITHUB_SETUP_GUIDE.md`
- `QUICK_START.md`
- `GETTING_STARTED.md`

## Best Practices

### ✅ DO
- Keep only essential, current documentation in root
- Archive historical/outdated files
- Consolidate duplicate content
- Use `docs/` for all documentation
- Update README.md as single source of truth

### ❌ DON'T
- Create multiple status files
- Keep temporary "what I did" files
- Duplicate content across files
- Leave outdated files in root
- Create files for every small update

## Maintenance

Run cleanup script periodically:
```bash
python3 scripts/cleanup_docs.py
```

Or manually archive files that are:
- Status updates older than 1 week
- Duplicate content
- Temporary/one-time use
- Historical (phases, milestones)
