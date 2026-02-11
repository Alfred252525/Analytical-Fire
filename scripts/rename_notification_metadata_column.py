#!/usr/bin/env python3
"""
Database Migration: Rename metadata column to notification_metadata in notifications table
Fixes SQLAlchemy reserved name conflict
"""

import os
import sys
from sqlalchemy import text

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from app.database import engine

def migrate():
    """Rename metadata column to notification_metadata"""
    print("Starting notification metadata column migration...")
    
    with engine.connect() as conn:
        # Check if old column exists
        check_old_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='notifications' AND column_name='metadata'
        """)
        old_exists = conn.execute(check_old_query).fetchone()
        
        # Check if new column already exists
        check_new_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='notifications' AND column_name='notification_metadata'
        """)
        new_exists = conn.execute(check_new_query).fetchone()
        
        if new_exists:
            print("✅ notification_metadata column already exists. Migration not needed.")
            if old_exists:
                print("⚠️  Old 'metadata' column still exists. Consider dropping it manually if safe.")
            return
        
        if not old_exists:
            print("⚠️  Old 'metadata' column not found. Creating new 'notification_metadata' column...")
            # Create new column if old doesn't exist
            alter_query = text("""
                ALTER TABLE notifications 
                ADD COLUMN notification_metadata TEXT
            """)
            conn.execute(alter_query)
            conn.commit()
            print("✅ Created notification_metadata column.")
            return
        
        # Rename column
        print("Renaming metadata column to notification_metadata...")
        alter_query = text("""
            ALTER TABLE notifications 
            RENAME COLUMN metadata TO notification_metadata
        """)
        conn.execute(alter_query)
        conn.commit()
        
        print("✅ Migration complete! Column renamed from 'metadata' to 'notification_metadata'.")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
