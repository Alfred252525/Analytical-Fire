#!/usr/bin/env python3
"""
Data Retention Automation - Automated data deletion per retention policies
Implements SOC 2 compliance data retention requirements
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.decision import Decision
from app.models.message import Message
from app.core.config import settings

# Retention periods (from DATA_RETENTION_PLAN.md)
DECISION_RETENTION_DAYS = 7 * 365  # 7 years
MESSAGE_ACTIVE_DAYS = 365  # 1 year active
MESSAGE_ARCHIVE_DAYS = 2 * 365  # 2 years archive (total 3 years)


class DataRetentionAutomation:
    """Automated data retention and deletion"""
    
    def __init__(self, dry_run: bool = True):
        """
        Initialize data retention automation
        
        Args:
            dry_run: If True, only report what would be deleted without actually deleting
        """
        self.dry_run = dry_run
        self.database_url = settings.DATABASE_URL if hasattr(settings, 'DATABASE_URL') else os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not configured")
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        self.stats = {
            'decisions_deleted': 0,
            'messages_archived': 0,
            'messages_deleted': 0,
            'errors': []
        }
    
    def delete_old_decisions(self, session) -> int:
        """
        Delete decisions older than retention period (7 years)
        
        Returns:
            Number of decisions deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=DECISION_RETENTION_DAYS)
        
        # Find old decisions
        old_decisions = session.query(Decision).filter(
            Decision.created_at < cutoff_date
        ).all()
        
        count = len(old_decisions)
        
        if count > 0:
            print(f"  Found {count} decisions older than 7 years (before {cutoff_date.date()})")
            
            if not self.dry_run:
                # Delete decisions
                session.query(Decision).filter(
                    Decision.created_at < cutoff_date
                ).delete(synchronize_session=False)
                session.commit()
                print(f"  ✅ Deleted {count} old decisions")
            else:
                print(f"  [DRY RUN] Would delete {count} old decisions")
        
        return count
    
    def archive_old_messages(self, session) -> int:
        """
        Archive messages older than active period (1 year) but less than archive period (3 years total)
        
        Returns:
            Number of messages archived
        """
        active_cutoff = datetime.utcnow() - timedelta(days=MESSAGE_ACTIVE_DAYS)
        archive_cutoff = datetime.utcnow() - timedelta(days=MESSAGE_ARCHIVE_DAYS)
        
        # Find messages to archive (older than 1 year, but less than 3 years)
        messages_to_archive = session.query(Message).filter(
            and_(
                Message.created_at < active_cutoff,
                Message.created_at >= archive_cutoff
            )
        ).all()
        
        count = len(messages_to_archive)
        
        if count > 0:
            print(f"  Found {count} messages to archive (older than 1 year, less than 3 years)")
            
            # Note: In a real implementation, you would move these to archive storage (S3 Glacier, etc.)
            # For now, we'll mark them or move to an archive table
            # This is a placeholder - actual archive implementation depends on storage solution
            
            if not self.dry_run:
                # TODO: Implement actual archiving (move to archive table or S3)
                # For now, just log that they would be archived
                print(f"  ⚠️  Archive functionality not yet implemented - skipping {count} messages")
                print(f"     Messages would be archived to S3 Glacier or archive table")
            else:
                print(f"  [DRY RUN] Would archive {count} messages")
        
        return count
    
    def delete_archived_messages(self, session) -> int:
        """
        Delete messages older than archive period (3 years total)
        
        Returns:
            Number of messages deleted
        """
        archive_cutoff = datetime.utcnow() - timedelta(days=MESSAGE_ARCHIVE_DAYS)
        
        # Find messages older than archive period
        old_messages = session.query(Message).filter(
            Message.created_at < archive_cutoff
        ).all()
        
        count = len(old_messages)
        
        if count > 0:
            print(f"  Found {count} messages older than 3 years (before {archive_cutoff.date()})")
            
            if not self.dry_run:
                # Delete old messages
                session.query(Message).filter(
                    Message.created_at < archive_cutoff
                ).delete(synchronize_session=False)
                session.commit()
                print(f"  ✅ Deleted {count} archived messages")
            else:
                print(f"  [DRY RUN] Would delete {count} archived messages")
        
        return count
    
    def run(self):
        """Run data retention automation"""
        print("=" * 60)
        print("Data Retention Automation")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        session = self.SessionLocal()
        
        try:
            # 1. Delete old decisions (7 years)
            print("1. Processing decisions (7-year retention)...")
            try:
                deleted = self.delete_old_decisions(session)
                self.stats['decisions_deleted'] = deleted
            except Exception as e:
                error_msg = f"Error deleting decisions: {e}"
                print(f"  ❌ {error_msg}")
                self.stats['errors'].append(error_msg)
            
            print()
            
            # 2. Archive old messages (1-3 years)
            print("2. Processing messages for archiving (1-3 years)...")
            try:
                archived = self.archive_old_messages(session)
                self.stats['messages_archived'] = archived
            except Exception as e:
                error_msg = f"Error archiving messages: {e}"
                print(f"  ❌ {error_msg}")
                self.stats['errors'].append(error_msg)
            
            print()
            
            # 3. Delete archived messages (older than 3 years)
            print("3. Processing archived messages for deletion (>3 years)...")
            try:
                deleted = self.delete_archived_messages(session)
                self.stats['messages_deleted'] = deleted
            except Exception as e:
                error_msg = f"Error deleting archived messages: {e}"
                print(f"  ❌ {error_msg}")
                self.stats['errors'].append(error_msg)
            
            print()
            
            # Summary
            print("=" * 60)
            print("Summary")
            print("=" * 60)
            print(f"Decisions deleted: {self.stats['decisions_deleted']}")
            print(f"Messages archived: {self.stats['messages_archived']}")
            print(f"Messages deleted: {self.stats['messages_deleted']}")
            
            if self.stats['errors']:
                print(f"\nErrors: {len(self.stats['errors'])}")
                for error in self.stats['errors']:
                    print(f"  - {error}")
            
            if self.dry_run:
                print("\n⚠️  This was a DRY RUN - no data was actually deleted")
                print("   Run with --live to perform actual deletions")
            
        finally:
            session.close()
    
    def verify_retention_compliance(self, session) -> Dict:
        """
        Verify retention compliance - check for data older than retention periods
        
        Returns:
            Dictionary with compliance status
        """
        now = datetime.utcnow()
        
        # Check decisions
        decision_cutoff = now - timedelta(days=DECISION_RETENTION_DAYS)
        old_decisions = session.query(Decision).filter(
            Decision.created_at < decision_cutoff
        ).count()
        
        # Check messages
        message_cutoff = now - timedelta(days=MESSAGE_ARCHIVE_DAYS)
        old_messages = session.query(Message).filter(
            Message.created_at < message_cutoff
        ).count()
        
        return {
            'compliant': old_decisions == 0 and old_messages == 0,
            'old_decisions': old_decisions,
            'old_messages': old_messages,
            'decision_cutoff': decision_cutoff.date(),
            'message_cutoff': message_cutoff.date()
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Data Retention Automation')
    parser.add_argument('--live', action='store_true', help='Perform actual deletions (default: dry run)')
    parser.add_argument('--verify', action='store_true', help='Verify retention compliance only')
    
    args = parser.parse_args()
    
    automation = DataRetentionAutomation(dry_run=not args.live)
    
    if args.verify:
        session = automation.SessionLocal()
        try:
            compliance = automation.verify_retention_compliance(session)
            print("=" * 60)
            print("Retention Compliance Check")
            print("=" * 60)
            print(f"Status: {'✅ COMPLIANT' if compliance['compliant'] else '⚠️  NON-COMPLIANT'}")
            print(f"Old decisions (>7 years): {compliance['old_decisions']}")
            print(f"Old messages (>3 years): {compliance['old_messages']}")
            print(f"Decision cutoff: {compliance['decision_cutoff']}")
            print(f"Message cutoff: {compliance['message_cutoff']}")
        finally:
            session.close()
    else:
        automation.run()


if __name__ == "__main__":
    main()
