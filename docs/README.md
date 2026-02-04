# Documentation

This directory contains all platform documentation.

## Structure

### Main Documentation
- `getting-started.md` - Getting started guide
- `api-reference.md` - API documentation
- `index.md` - Documentation index
- `examples.md` - Code examples
- `STRUCTURE.md` - Documentation structure guide

### Setup Guides
- `setup/` - Setup guides (AWS, Domain, GitHub, etc.)

### Deployment Guides
- `deployment/` - Deployment documentation

### Outreach Content
- `outreach_content/` - Ready-to-share content for Reddit, Discord, etc.

### Archive
- `archive/` - Historical/outdated files
  - `historical/` - Old phase/progress files
  - `status-updates/` - Old status files
  - `redundant/` - Duplicate/redundant files

## Maintenance

Run cleanup script to archive outdated files:
```bash
python3 scripts/cleanup_docs.py
```

## Standards

- All documentation goes here
- Root directory stays clean
- Archive instead of delete
- Consolidate duplicate content
- Single source of truth
