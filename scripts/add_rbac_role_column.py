#!/usr/bin/env python3
"""
Database Migration: Add role column to ai_instances table
Adds RBAC support to existing database
"""

import os
import sys
from sqlalchemy import text

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from app.database import engine
from app.core.config import settings

def migrate():
    """Add role column to ai_instances table"""
    print("Starting RBAC migration...")
    
    with engine.connect() as conn:
        # Check if column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='ai_instances' AND column_name='role'
        """)
        result = conn.execute(check_query).fetchone()
        
        if result:
            print("✅ Role column already exists. Migration not needed.")
            return
        
        # Add role column with default value
        print("Adding role column to ai_instances table...")
        alter_query = text("""
            ALTER TABLE ai_instances 
            ADD COLUMN role VARCHAR DEFAULT 'user' NOT NULL
        """)
        conn.execute(alter_query)
        conn.commit()
        
        # Update existing records to have 'user' role (if any are NULL)
        print("Setting default role for existing instances...")
        update_query = text("""
            UPDATE ai_instances 
            SET role = 'user' 
            WHERE role IS NULL
        """)
        conn.execute(update_query)
        conn.commit()
        
        print("✅ Migration complete! All instances now have 'user' role by default.")
        print("   Use admin endpoints to promote instances to admin/moderator roles.")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
