"""
CLI command for git hooks installation
"""

import sys
import argparse
from pathlib import Path

# Add SDK to path
sdk_path = Path(__file__).parent
sys.path.insert(0, str(sdk_path))

try:
    from .git_hooks import install_git_hooks, uninstall_git_hooks, GitHooks
    from .auto_init import get_auto_client
except ImportError:
    # Try absolute imports if relative fails
    try:
        from git_hooks import install_git_hooks, uninstall_git_hooks, GitHooks
        from auto_init import get_auto_client
    except ImportError as e:
        print(f"❌ Error importing modules: {e}", file=sys.stderr)
        sys.exit(1)


def install_hooks_cli():
    """CLI entry point for installing git hooks"""
    parser = argparse.ArgumentParser(
        description='Install git hooks for automatic knowledge extraction',
        prog='aifai-install-hooks'
    )
    parser.add_argument(
        '--repo',
        type=str,
        help='Path to git repository (default: current directory)'
    )
    parser.add_argument(
        '--no-auto-share',
        action='store_true',
        help='Install hooks but do not auto-share (extract only)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Check hook installation status'
    )
    parser.add_argument(
        '--uninstall',
        action='store_true',
        help='Uninstall git hooks'
    )
    
    args = parser.parse_args()
    
    hooks = GitHooks(repo_path=args.repo)
    
    if args.status:
        # Check status
        status = hooks.get_hook_status()
        print("📊 Git Hooks Status")
        print("=" * 50)
        print(f"Repository: {status.get('repo_path', 'N/A')}")
        print(f"Is Git Repo: {status.get('is_git_repo', False)}")
        print(f"Post-Commit Hook: {'✅ Installed' if status.get('post_commit_exists') else '❌ Not installed'}")
        print(f"Pre-Commit Hook: {'✅ Installed' if status.get('pre_commit_exists') else '❌ Not installed'}")
        return
    
    if args.uninstall:
        # Uninstall hooks
        result = hooks.uninstall_hooks()
        if result['success']:
            print("✅ Git hooks uninstalled successfully")
            if result.get('removed'):
                print(f"   Removed: {', '.join(result['removed'])}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
        return
    
    # Install hooks
    print("🔧 Installing AIFAI Git Hooks...")
    print("=" * 50)
    
    # Get client for auto-sharing
    client = None
    if not args.no_auto_share:
        try:
            client = get_auto_client()
            print("✅ Platform client initialized")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize platform client: {e}")
            print("   Hooks will be installed but knowledge won't be auto-shared")
            print("   You can manually share knowledge later")
    
    result = hooks.install_hooks(client=client, auto_share=not args.no_auto_share)
    
    if result['success']:
        print("✅ Git hooks installed successfully!")
        print()
        print("📝 What happens now:")
        print("   • Every commit will automatically extract knowledge")
        if not args.no_auto_share:
            print("   • Knowledge will be automatically shared to platform")
        else:
            print("   • Knowledge will be extracted but not shared (use --no-auto-share)")
        print()
        print("💡 Tips:")
        print("   • Use '[skip aifai]' in commit message to skip extraction")
        print("   • Use '[no-share]' in commit message to skip sharing")
        print("   • Check status: aifai-install-hooks --status")
        print("   • Uninstall: aifai-install-hooks --uninstall")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        print(f"   {result.get('message', '')}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    install_hooks_cli()
