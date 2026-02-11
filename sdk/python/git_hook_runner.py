#!/usr/bin/env python3
"""
Git hook runner - Extracts knowledge from commits and shares to platform
This script is called by git hooks automatically
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add SDK to path
sdk_path = Path(__file__).parent
sys.path.insert(0, str(sdk_path))

try:
    from git_knowledge_extractor import GitKnowledgeExtractor
    from auto_init import get_auto_client
except ImportError:
    # If imports fail, silently exit (hooks shouldn't break git)
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Extract knowledge from git commit')
    parser.add_argument('--commit', required=True, help='Commit hash')
    parser.add_argument('--repo', required=True, help='Repository path')
    parser.add_argument('--auto-share', type=str, default='true', help='Auto-share to platform')
    
    args = parser.parse_args()
    
    # Convert string to bool
    auto_share = args.auto_share.lower() in ('true', '1', 'yes', 'on')
    
    try:
        # Initialize extractor
        extractor = GitKnowledgeExtractor(repo_path=args.repo)
        
        # Get commit message first to check if trivial
        try:
            commit_msg = subprocess.check_output(
                ['git', 'log', '-1', '--pretty=%B', args.commit],
                cwd=args.repo,
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            commit_msg = ""
        
        # Check if commit is trivial (skip if so)
        trivial_keywords = ['typo', 'format', 'whitespace', 'spacing', 'lint', 'style', 'wip', 'test']
        commit_msg_lower = commit_msg.lower()
        
        # Skip if commit message indicates trivial change
        if any(keyword in commit_msg_lower for keyword in trivial_keywords):
            # Trivial commit, skip extraction
            sys.exit(0)
        
        # Extract knowledge from commit
        knowledge = extractor.extract_from_diff(commit_hash=args.commit)
        
        if not knowledge:
            # No meaningful knowledge extracted
            sys.exit(0)
        
        if auto_share:
            # Auto-share to platform
            try:
                client = get_auto_client()
                result = client.share_knowledge(
                    title=knowledge['title'],
                    content=knowledge['content'],
                    category=knowledge['category'],
                    tags=knowledge.get('tags', [])
                )
                # Print to stderr so it doesn't interfere with git output
                print(f"✅ Shared knowledge: {knowledge['title'][:50]}...", file=sys.stderr)
            except Exception as e:
                # Don't fail git commit if sharing fails
                print(f"⚠️  Could not share knowledge: {e}", file=sys.stderr)
        
    except Exception as e:
        # Don't break git hooks if extraction fails
        print(f"⚠️  Knowledge extraction error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
