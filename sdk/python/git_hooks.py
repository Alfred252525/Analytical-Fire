"""
Git hooks for automatic knowledge extraction and sharing
Automatically extracts knowledge from git commits and shares to platform
"""

import os
import sys
import subprocess
import json
from typing import Optional, Dict, Any, List
from pathlib import Path


class GitHooks:
    """
    Install and manage git hooks for automatic knowledge extraction.
    
    This enables automatic knowledge sharing from every commit:
    - Pre-commit: Analyze commit for knowledge extraction
    - Post-commit: Extract and share knowledge to platform
    """
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize git hooks manager.
        
        Args:
            repo_path: Path to git repository (default: current directory)
        """
        self.repo_path = Path(repo_path or os.getcwd()).resolve()
        self.git_dir = self.repo_path / '.git'
        self.hooks_dir = self.git_dir / 'hooks'
        
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        return self.git_dir.exists() and self.git_dir.is_dir()
    
    def install_hooks(self, client=None, auto_share: bool = True) -> Dict[str, Any]:
        """
        Install git hooks for automatic knowledge extraction.
        
        Args:
            client: AIFAIClient instance (optional, will auto-initialize if not provided)
            auto_share: Automatically share knowledge to platform (default: True)
            
        Returns:
            Dict with installation status
        """
        if not self.is_git_repo():
            return {
                "success": False,
                "error": "Not a git repository",
                "message": "Run this command from within a git repository"
            }
        
        # Ensure hooks directory exists
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        
        # Install post-commit hook
        post_commit_installed = self._install_post_commit_hook(client, auto_share)
        
        # Install pre-commit hook (optional, for analysis)
        pre_commit_installed = self._install_pre_commit_hook()
        
        return {
            "success": post_commit_installed and pre_commit_installed,
            "repo_path": str(self.repo_path),
            "hooks_dir": str(self.hooks_dir),
            "post_commit_installed": post_commit_installed,
            "pre_commit_installed": pre_commit_installed,
            "message": "Git hooks installed successfully" if post_commit_installed else "Failed to install hooks"
        }
    
    def uninstall_hooks(self) -> Dict[str, Any]:
        """
        Uninstall git hooks.
        
        Returns:
            Dict with uninstallation status
        """
        if not self.is_git_repo():
            return {
                "success": False,
                "error": "Not a git repository"
            }
        
        post_commit_hook = self.hooks_dir / 'post-commit'
        pre_commit_hook = self.hooks_dir / 'pre-commit'
        
        removed = []
        
        if post_commit_hook.exists():
            # Check if it's our hook before removing
            try:
                content = post_commit_hook.read_text()
                if 'aifai-client' in content or 'GitHooks' in content:
                    post_commit_hook.unlink()
                    removed.append('post-commit')
            except Exception:
                pass
        
        if pre_commit_hook.exists():
            try:
                content = pre_commit_hook.read_text()
                if 'aifai-client' in content or 'GitHooks' in content:
                    pre_commit_hook.unlink()
                    removed.append('pre-commit')
            except Exception:
                pass
        
        return {
            "success": True,
            "removed": removed,
            "message": f"Removed hooks: {', '.join(removed) if removed else 'No hooks found'}"
        }
    
    def _install_post_commit_hook(self, client=None, auto_share: bool = True) -> bool:
        """Install post-commit hook for knowledge extraction"""
        hook_path = self.hooks_dir / 'post-commit'
        
        # Get Python executable
        python_exe = sys.executable
        
        # Get path to this module
        sdk_path = Path(__file__).parent
        hook_script_path = sdk_path / 'git_hook_runner.py'
        
        # Create hook script if it doesn't exist
        if not hook_script_path.exists():
            self._create_hook_runner_script(hook_script_path)
        
        # Create post-commit hook
        hook_content = f"""#!/bin/bash
# AIFAI Git Hook - Automatic Knowledge Extraction
# This hook extracts knowledge from commits and shares to platform

# Get the latest commit
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)

# Skip if commit message contains [skip aifai] or [no-share]
if echo "$COMMIT_MSG" | grep -qE '\\[skip aifai\\]|\\[no-share\\]'; then
    exit 0
fi

# Run knowledge extraction
{python_exe} "{hook_script_path}" --commit "$COMMIT_HASH" --repo "{self.repo_path}" --auto-share {"true" if auto_share else "false"}
"""
        
        try:
            hook_path.write_text(hook_content)
            hook_path.chmod(0o755)  # Make executable
            return True
        except Exception as e:
            print(f"Error installing post-commit hook: {e}")
            return False
    
    def _install_pre_commit_hook(self) -> bool:
        """Install pre-commit hook for commit analysis (optional)"""
        hook_path = self.hooks_dir / 'pre-commit'
        
        # Simple pre-commit hook that doesn't block commits
        # Just analyzes for knowledge potential
        hook_content = """#!/bin/bash
# AIFAI Pre-Commit Hook - Analyze commit for knowledge potential
# This hook doesn't block commits, just analyzes them

# Get staged changes
STAGED_FILES=$(git diff --cached --name-only)

# Check if meaningful changes (not just formatting)
MEANINGFUL_CHANGES=$(echo "$STAGED_FILES" | grep -vE '\\.(md|txt|json|yaml|yml)$' | head -1)

if [ -z "$MEANINGFUL_CHANGES" ]; then
    # Only documentation changes, skip analysis
    exit 0
fi

# Allow commit to proceed
exit 0
"""
        
        try:
            hook_path.write_text(hook_content)
            hook_path.chmod(0o755)
            return True
        except Exception as e:
            print(f"Error installing pre-commit hook: {e}")
            return False
    
    def _create_hook_runner_script(self, script_path: Path):
        """Create the hook runner script that extracts and shares knowledge"""
        script_content = '''#!/usr/bin/env python3
"""
Git hook runner - Extracts knowledge from commits and shares to platform
This script is called by git hooks automatically
"""

import sys
import os
import argparse
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
    parser.add_argument('--auto-share', type=bool, default=True, help='Auto-share to platform')
    
    args = parser.parse_args()
    
    try:
        # Initialize extractor
        extractor = GitKnowledgeExtractor(repo_path=args.repo)
        
        # Extract knowledge from commit
        knowledge = extractor.extract_from_diff(commit_hash=args.commit)
        
        if not knowledge:
            # No meaningful knowledge extracted
            sys.exit(0)
        
        # Check if commit is trivial (skip if so)
        commit_msg = subprocess.check_output(
            ['git', 'log', '-1', '--pretty=%B', args.commit],
            cwd=args.repo,
            text=True
        ).strip()
        
        trivial_keywords = ['typo', 'format', 'whitespace', 'spacing', 'lint', 'style']
        if any(keyword in commit_msg.lower() for keyword in trivial_keywords):
            # Trivial commit, skip sharing
            sys.exit(0)
        
        if args.auto_share:
            # Auto-share to platform
            try:
                client = get_auto_client()
                result = client.share_knowledge(
                    title=knowledge['title'],
                    content=knowledge['content'],
                    category=knowledge['category'],
                    tags=knowledge.get('tags', [])
                )
                print(f"✅ Shared knowledge: {knowledge['title'][:50]}...")
            except Exception as e:
                # Don't fail git commit if sharing fails
                print(f"⚠️  Could not share knowledge: {e}", file=sys.stderr)
        
    except Exception as e:
        # Don't break git hooks if extraction fails
        print(f"⚠️  Knowledge extraction error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
'''
        
        script_path.write_text(script_content)
        script_path.chmod(0o755)
    
    def get_hook_status(self) -> Dict[str, Any]:
        """Get status of installed hooks"""
        if not self.is_git_repo():
            return {
                "is_git_repo": False,
                "hooks_installed": False
            }
        
        post_commit = self.hooks_dir / 'post-commit'
        pre_commit = self.hooks_dir / 'pre-commit'
        
        return {
            "is_git_repo": True,
            "repo_path": str(self.repo_path),
            "hooks_dir": str(self.hooks_dir),
            "post_commit_exists": post_commit.exists(),
            "pre_commit_exists": pre_commit.exists(),
            "hooks_installed": post_commit.exists() or pre_commit.exists()
        }


def install_git_hooks(repo_path: Optional[str] = None, client=None, auto_share: bool = True) -> Dict[str, Any]:
    """
    Convenience function to install git hooks.
    
    Args:
        repo_path: Path to git repository (default: current directory)
        client: AIFAIClient instance (optional)
        auto_share: Automatically share knowledge (default: True)
        
    Returns:
        Installation status dict
        
    Example:
        >>> from aifai_client import get_auto_client
        >>> from aifai_client.git_hooks import install_git_hooks
        >>> 
        >>> client = get_auto_client()
        >>> result = install_git_hooks(client=client)
        >>> print(result['message'])
    """
    hooks = GitHooks(repo_path=repo_path)
    return hooks.install_hooks(client=client, auto_share=auto_share)


def uninstall_git_hooks(repo_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to uninstall git hooks.
    
    Args:
        repo_path: Path to git repository (default: current directory)
        
    Returns:
        Uninstallation status dict
    """
    hooks = GitHooks(repo_path=repo_path)
    return hooks.uninstall_hooks()
