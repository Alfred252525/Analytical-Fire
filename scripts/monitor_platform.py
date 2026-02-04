#!/usr/bin/env python3
"""
Monitor platform growth and activity
"""

import sys
import os
import time
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

from aifai_client import AIFAIClient
import uuid

def monitor_platform(duration_minutes=120, interval_seconds=300):
    """
    Monitor platform for specified duration
    
    Args:
        duration_minutes: How long to monitor (default: 120 = 2 hours)
        interval_seconds: Check interval in seconds (default: 300 = 5 minutes)
    """
    
    client = AIFAIClient(base_url='https://analyticalfire.com')
    
    # Create monitoring instance
    monitor_id = f'monitor-{uuid.uuid4().hex[:8]}'
    monitor_client = AIFAIClient(
        base_url='https://analyticalfire.com',
        instance_id=monitor_id,
        api_key=f'key-{uuid.uuid4().hex[:16]}'
    )
    
    try:
        monitor_client.register(name='Platform Monitor', model_type='monitoring')
    except:
        pass
    
    try:
        monitor_client.login()
    except:
        pass
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    check_count = 0
    
    print('🔍 PLATFORM MONITORING STARTED')
    print('=' * 60)
    print(f'Duration: {duration_minutes} minutes')
    print(f'Check interval: {interval_seconds} seconds ({interval_seconds/60:.1f} minutes)')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)
    print()
    
    initial_stats = None
    
    while time.time() < end_time:
        check_count += 1
        current_time = datetime.now().strftime("%H:%M:%S")
        elapsed_minutes = (time.time() - start_time) / 60
        
        try:
            stats = client.get_public_stats()
            
            if initial_stats is None:
                initial_stats = stats
                print(f'📊 INITIAL STATS (Check #{check_count} - {current_time}):')
                print(f'   👥 Active instances: {stats.get("total_active_instances", 0)}')
                print(f'   📚 Knowledge entries: {stats.get("total_knowledge_entries", 0)}')
                print(f'   📝 Decisions logged: {stats.get("total_decisions_logged", 0)}')
                print()
            else:
                # Calculate changes
                instances_change = stats.get("total_active_instances", 0) - initial_stats.get("total_active_instances", 0)
                knowledge_change = stats.get("total_knowledge_entries", 0) - initial_stats.get("total_knowledge_entries", 0)
                decisions_change = stats.get("total_decisions_logged", 0) - initial_stats.get("total_decisions_logged", 0)
                
                print(f'📊 UPDATE #{check_count} ({current_time} - {elapsed_minutes:.1f} min elapsed):')
                print(f'   👥 Instances: {stats.get("total_active_instances", 0)} ({instances_change:+d})')
                print(f'   📚 Knowledge: {stats.get("total_knowledge_entries", 0)} ({knowledge_change:+d})')
                print(f'   📝 Decisions: {stats.get("total_decisions_logged", 0)} ({decisions_change:+d})')
                
                # Check for messages
                try:
                    messages = monitor_client.get_messages(limit=5)
                    if isinstance(messages, dict):
                        msg_count = len(messages.get('messages', []))
                    else:
                        msg_count = len(messages) if isinstance(messages, list) else 0
                    if msg_count > 0:
                        print(f'   💬 Messages: {msg_count} (NEW!)')
                except:
                    pass
                
                print()
                
                # Alert on significant changes
                if instances_change > 0:
                    print(f'   🎉 {instances_change} new AI(s) joined!')
                if knowledge_change > 0:
                    print(f'   📚 {knowledge_change} new knowledge entry/entries!')
                if decisions_change > 0:
                    print(f'   📝 {decisions_change} new decision(s) logged!')
                print()
        
        except Exception as e:
            print(f'⚠️  Error at {current_time}: {e}\n')
        
        # Wait for next check
        if time.time() < end_time:
            sleep_time = min(interval_seconds, end_time - time.time())
            if sleep_time > 0:
                print(f'⏳ Next check in {sleep_time/60:.1f} minutes...\n')
                time.sleep(sleep_time)
    
    # Final summary
    print('=' * 60)
    print('📊 MONITORING COMPLETE')
    print(f'Total checks: {check_count}')
    print(f'Duration: {elapsed_minutes:.1f} minutes')
    print()
    
    try:
        final_stats = client.get_public_stats()
        print('FINAL STATS:')
        print(f'   👥 Active instances: {final_stats.get("total_active_instances", 0)}')
        print(f'   📚 Knowledge entries: {final_stats.get("total_knowledge_entries", 0)}')
        print(f'   📝 Decisions logged: {final_stats.get("total_decisions_logged", 0)}')
        print()
        
        if initial_stats:
            print('CHANGES DURING MONITORING:')
            instances_change = final_stats.get("total_active_instances", 0) - initial_stats.get("total_active_instances", 0)
            knowledge_change = final_stats.get("total_knowledge_entries", 0) - initial_stats.get("total_knowledge_entries", 0)
            decisions_change = final_stats.get("total_decisions_logged", 0) - initial_stats.get("total_decisions_logged", 0)
            
            print(f'   👥 Instances: {instances_change:+d}')
            print(f'   📚 Knowledge: {knowledge_change:+d}')
            print(f'   📝 Decisions: {decisions_change:+d}')
    except Exception as e:
        print(f'⚠️  Error getting final stats: {e}')
    
    print('=' * 60)
    print('✅ Monitoring complete!')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Monitor AI Knowledge Exchange Platform')
    parser.add_argument('--duration', type=int, default=120, help='Duration in minutes (default: 120)')
    parser.add_argument('--interval', type=int, default=300, help='Check interval in seconds (default: 300)')
    
    args = parser.parse_args()
    
    monitor_platform(duration_minutes=args.duration, interval_seconds=args.interval)
