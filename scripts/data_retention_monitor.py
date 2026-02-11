#!/usr/bin/env python3
"""
Data Retention Monitoring - Monitor compliance with retention policies
Implements SOC 2 compliance monitoring requirements
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.decision import Decision
from app.models.message import Message
from app.core.config import settings

# Retention periods
DECISION_RETENTION_DAYS = 7 * 365  # 7 years
MESSAGE_ACTIVE_DAYS = 365  # 1 year active
MESSAGE_ARCHIVE_DAYS = 2 * 365  # 2 years archive (total 3 years)


class DataRetentionMonitor:
    """Monitor data retention compliance"""
    
    def __init__(self):
        """Initialize retention monitor"""
        self.database_url = settings.DATABASE_URL if hasattr(settings, 'DATABASE_URL') else os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not configured")
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def check_compliance(self) -> Dict:
        """
        Check retention compliance
        
        Returns:
            Dictionary with compliance status and metrics
        """
        session = self.SessionLocal()
        
        try:
            now = datetime.utcnow()
            
            # Decision retention check
            decision_cutoff = now - timedelta(days=DECISION_RETENTION_DAYS)
            old_decisions = session.query(Decision).filter(
                Decision.created_at < decision_cutoff
            ).count()
            total_decisions = session.query(Decision).count()
            
            # Message retention check
            message_archive_cutoff = now - timedelta(days=MESSAGE_ACTIVE_DAYS)
            message_delete_cutoff = now - timedelta(days=MESSAGE_ARCHIVE_DAYS)
            
            messages_to_archive = session.query(Message).filter(
                Message.created_at < message_archive_cutoff
            ).count()
            
            old_messages = session.query(Message).filter(
                Message.created_at < message_delete_cutoff
            ).count()
            
            total_messages = session.query(Message).count()
            
            # Age distribution
            decision_age_distribution = {
                '< 1 year': session.query(Decision).filter(
                    Decision.created_at >= now - timedelta(days=365)
                ).count(),
                '1-3 years': session.query(Decision).filter(
                    and_(
                        Decision.created_at >= now - timedelta(days=3*365),
                        Decision.created_at < now - timedelta(days=365)
                    )
                ).count(),
                '3-7 years': session.query(Decision).filter(
                    and_(
                        Decision.created_at >= now - timedelta(days=7*365),
                        Decision.created_at < now - timedelta(days=3*365)
                    )
                ).count(),
                '> 7 years': old_decisions
            }
            
            message_age_distribution = {
                '< 1 year': session.query(Message).filter(
                    Message.created_at >= now - timedelta(days=365)
                ).count(),
                '1-3 years': session.query(Message).filter(
                    and_(
                        Message.created_at >= now - timedelta(days=3*365),
                        Message.created_at < now - timedelta(days=365)
                    )
                ).count(),
                '> 3 years': old_messages
            }
            
            # Compliance status
            compliant = old_decisions == 0 and old_messages == 0
            
            return {
                'compliant': compliant,
                'check_date': now.isoformat(),
                'decisions': {
                    'total': total_decisions,
                    'old_count': old_decisions,
                    'cutoff_date': decision_cutoff.date().isoformat(),
                    'age_distribution': decision_age_distribution,
                    'compliant': old_decisions == 0
                },
                'messages': {
                    'total': total_messages,
                    'to_archive': messages_to_archive,
                    'old_count': old_messages,
                    'archive_cutoff': message_archive_cutoff.date().isoformat(),
                    'delete_cutoff': message_delete_cutoff.date().isoformat(),
                    'age_distribution': message_age_distribution,
                    'compliant': old_messages == 0
                }
            }
        finally:
            session.close()
    
    def generate_report(self) -> str:
        """Generate compliance report"""
        compliance = self.check_compliance()
        
        report = []
        report.append("=" * 60)
        report.append("Data Retention Compliance Report")
        report.append("=" * 60)
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Status: {'✅ COMPLIANT' if compliance['compliant'] else '⚠️  NON-COMPLIANT'}")
        report.append("")
        
        # Decisions
        report.append("Decisions:")
        report.append(f"  Total: {compliance['decisions']['total']}")
        report.append(f"  Old (>7 years): {compliance['decisions']['old_count']}")
        report.append(f"  Cutoff date: {compliance['decisions']['cutoff_date']}")
        report.append(f"  Status: {'✅ Compliant' if compliance['decisions']['compliant'] else '❌ Non-compliant'}")
        report.append("  Age Distribution:")
        for age_range, count in compliance['decisions']['age_distribution'].items():
            report.append(f"    {age_range}: {count}")
        report.append("")
        
        # Messages
        report.append("Messages:")
        report.append(f"  Total: {compliance['messages']['total']}")
        report.append(f"  To archive (1-3 years): {compliance['messages']['to_archive']}")
        report.append(f"  Old (>3 years): {compliance['messages']['old_count']}")
        report.append(f"  Archive cutoff: {compliance['messages']['archive_cutoff']}")
        report.append(f"  Delete cutoff: {compliance['messages']['delete_cutoff']}")
        report.append(f"  Status: {'✅ Compliant' if compliance['messages']['compliant'] else '❌ Non-compliant'}")
        report.append("  Age Distribution:")
        for age_range, count in compliance['messages']['age_distribution'].items():
            report.append(f"    {age_range}: {count}")
        report.append("")
        
        # Recommendations
        if not compliance['compliant']:
            report.append("Recommendations:")
            if compliance['decisions']['old_count'] > 0:
                report.append(f"  - Run data retention automation to delete {compliance['decisions']['old_count']} old decisions")
            if compliance['messages']['old_count'] > 0:
                report.append(f"  - Run data retention automation to delete {compliance['messages']['old_count']} old messages")
            if compliance['messages']['to_archive'] > 0:
                report.append(f"  - Archive {compliance['messages']['to_archive']} messages (1-3 years old)")
        
        return "\n".join(report)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Data Retention Compliance Monitor')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    monitor = DataRetentionMonitor()
    
    if args.json:
        import json
        compliance = monitor.check_compliance()
        print(json.dumps(compliance, indent=2))
    else:
        report = monitor.generate_report()
        print(report)
        
        # Exit with error code if non-compliant
        compliance = monitor.check_compliance()
        if not compliance['compliant']:
            sys.exit(1)


if __name__ == "__main__":
    main()
