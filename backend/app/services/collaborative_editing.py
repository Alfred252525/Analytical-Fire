"""
Collaborative editing service
Tracks concurrent edits and manages edit locks
"""

from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

class EditLock:
    """Represents an edit lock on a resource"""
    def __init__(self, resource_id: int, resource_type: str, editor_id: int):
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.editor_id = editor_id
        self.locked_at = datetime.utcnow()
        self.expires_at = self.locked_at + timedelta(minutes=5)  # 5 minute lock
    
    def is_expired(self) -> bool:
        """Check if lock has expired"""
        return datetime.utcnow() > self.expires_at
    
    def extend(self):
        """Extend lock expiration"""
        self.expires_at = datetime.utcnow() + timedelta(minutes=5)

class CollaborativeEditingManager:
    """Manages collaborative editing sessions"""
    
    def __init__(self):
        self.locks: Dict[str, EditLock] = {}  # resource_key -> EditLock
        self.watching: Dict[int, Set[str]] = defaultdict(set)  # instance_id -> set of resource_keys
    
    def acquire_lock(self, resource_id: int, resource_type: str, editor_id: int) -> bool:
        """
        Acquire edit lock on a resource
        
        Returns:
            True if lock acquired, False if already locked
        """
        resource_key = f"{resource_type}:{resource_id}"
        
        # Check if already locked
        if resource_key in self.locks:
            lock = self.locks[resource_key]
            if not lock.is_expired():
                if lock.editor_id == editor_id:
                    # Same editor, extend lock
                    lock.extend()
                    return True
                else:
                    # Different editor, lock exists
                    return False
            else:
                # Lock expired, remove it
                del self.locks[resource_key]
        
        # Acquire new lock
        self.locks[resource_key] = EditLock(resource_id, resource_type, editor_id)
        return True
    
    def release_lock(self, resource_id: int, resource_type: str, editor_id: int) -> bool:
        """
        Release edit lock on a resource
        
        Returns:
            True if lock released, False if not found or not owned
        """
        resource_key = f"{resource_type}:{resource_id}"
        
        if resource_key not in self.locks:
            return False
        
        lock = self.locks[resource_key]
        if lock.editor_id != editor_id:
            return False
        
        del self.locks[resource_key]
        return True
    
    def get_lock_owner(self, resource_id: int, resource_type: str) -> Optional[int]:
        """Get the current lock owner for a resource"""
        resource_key = f"{resource_type}:{resource_id}"
        
        if resource_key not in self.locks:
            return None
        
        lock = self.locks[resource_key]
        if lock.is_expired():
            del self.locks[resource_key]
            return None
        
        return lock.editor_id
    
    def watch_resource(self, instance_id: int, resource_id: int, resource_type: str):
        """Start watching a resource for changes"""
        resource_key = f"{resource_type}:{resource_id}"
        self.watching[instance_id].add(resource_key)
    
    def unwatch_resource(self, instance_id: int, resource_id: int, resource_type: str):
        """Stop watching a resource"""
        resource_key = f"{resource_type}:{resource_id}"
        self.watching[instance_id].discard(resource_key)
    
    def get_watchers(self, resource_id: int, resource_type: str) -> Set[int]:
        """Get all instances watching a resource"""
        resource_key = f"{resource_type}:{resource_id}"
        watchers = set()
        
        for instance_id, watched_resources in self.watching.items():
            if resource_key in watched_resources:
                watchers.add(instance_id)
        
        return watchers
    
    def cleanup_expired_locks(self):
        """Remove expired locks"""
        expired_keys = [
            key for key, lock in self.locks.items()
            if lock.is_expired()
        ]
        
        for key in expired_keys:
            del self.locks[key]

# Global collaborative editing manager
collaborative_manager = CollaborativeEditingManager()
