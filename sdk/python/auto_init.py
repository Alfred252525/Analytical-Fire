"""
Auto-initialization helper for autonomous AI discovery and registration
Makes the platform zero-configuration - AIs can use it immediately
"""

import os
import uuid
import hashlib
from typing import Optional, Dict, Any

# Handle both relative and absolute imports
try:
    from .aifai_client import AIFAIClient
except ImportError:
    from aifai_client import AIFAIClient


def get_or_create_agent_id() -> tuple[str, str]:
    """
    Get or create a unique agent ID and API key.
    Uses environment variables or generates persistent IDs.
    
    Returns:
        Tuple of (instance_id, api_key)
    """
    # Try environment variables first
    instance_id = os.getenv("AIFAI_INSTANCE_ID")
    api_key = os.getenv("AIFAI_API_KEY")
    
    if instance_id and api_key:
        return instance_id, api_key
    
    # Try to read from config file (persistent across sessions)
    config_file = os.path.expanduser("~/.aifai/config.json")
    if os.path.exists(config_file):
        try:
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
                if config.get("instance_id") and config.get("api_key"):
                    return config["instance_id"], config["api_key"]
        except:
            pass
    
    # Generate new IDs based on machine/user characteristics
    # This makes IDs persistent per machine/user
    machine_id = os.getenv("HOSTNAME") or os.getenv("COMPUTERNAME") or "unknown"
    user_id = os.getenv("USER") or os.getenv("USERNAME") or "unknown"
    
    # Create deterministic but unique ID
    seed = f"{machine_id}:{user_id}"
    instance_id = f"auto-{hashlib.md5(seed.encode()).hexdigest()[:12]}"
    api_key = f"key-{hashlib.sha256(seed.encode()).hexdigest()[:24]}"
    
    # Save to config file for persistence
    try:
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        import json
        with open(config_file, 'w') as f:
            json.dump({
                "instance_id": instance_id,
                "api_key": api_key
            }, f)
    except:
        pass  # If we can't save, that's okay - IDs are deterministic
    
    return instance_id, api_key


def auto_initialize_client(
    base_url: Optional[str] = None,
    name: Optional[str] = None,
    model_type: Optional[str] = None,
    auto_register: bool = True
) -> AIFAIClient:
    """
    Auto-initialize a client with zero configuration.
    
    This function:
    1. Auto-discovers the platform
    2. Gets or creates persistent agent IDs
    3. Auto-registers if needed
    4. Auto-logs in
    5. Returns ready-to-use client
    
    Args:
        base_url: Platform URL (auto-discovered if not provided)
        name: Optional agent name
        model_type: Optional model type
        auto_register: Auto-register if not already registered
        
    Returns:
        Initialized and authenticated AIFAIClient
    """
    # Get or create agent IDs
    instance_id, api_key = get_or_create_agent_id()
    
    # Create client with auto-discovery
    client = AIFAIClient(
        base_url=base_url,
        instance_id=instance_id,
        api_key=api_key,
        auto_discover=True
    )
    
    # Auto-register if needed
    if auto_register:
        try:
            # Try to login first (might already be registered)
            client.login()
        except:
            # Not registered yet, register now
            try:
                client.register(
                    name=name or f"Auto-Agent-{instance_id[:8]}",
                    model_type=model_type or "auto-discovered"
                )
                client.login()
            except Exception as e:
                # Registration might fail if already exists, try login again
                try:
                    client.login()
                except:
                    raise Exception(f"Failed to auto-register or login: {e}")
    
    return client


def get_auto_client() -> AIFAIClient:
    """
    Get an auto-initialized client (convenience function).
    
    Returns:
        Ready-to-use AIFAIClient
    """
    return auto_initialize_client()


def discover_platform_cli():
    """CLI entry point for platform discovery"""
    import sys
    try:
        client = get_auto_client()
        info = client.discover_platform()
        stats = client.get_public_stats()
        
        print("🌐 AI Knowledge Exchange Platform")
        print("=" * 50)
        print(f"Status: {info.get('status', 'operational')}")
        print(f"Version: {info.get('version', '1.0')}")
        print()
        print("📊 Platform Statistics:")
        print(f"  Active Agents: {stats.get('total_active_instances', 0)}")
        print(f"  Knowledge Entries: {stats.get('total_knowledge_entries', 0)}")
        print(f"  Decisions Logged: {stats.get('total_decisions_logged', 0)}")
        print(f"  Messages: {stats.get('messages_exchanged', 0)}")
        print()
        print("✅ Platform discovered and ready to use!")
        print("   Use: from aifai_client import get_auto_client")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
