#!/usr/bin/env python3
"""
Analyze AI-to-AI Messages
Examines actual message content to assess intelligence and problem-solving
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from collections import Counter, defaultdict

# Add backend to path for database access
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

try:
    from app.database import SessionLocal, engine
    from app.models.message import Message
    from app.models.ai_instance import AIInstance
    from sqlalchemy import func, desc, and_, not_
    from sqlalchemy.orm import joinedload
except ImportError as e:
    print(f"❌ Error importing database modules: {e}")
    print("   Make sure you're running from the project root and backend dependencies are installed")
    sys.exit(1)

def get_recent_messages(db, limit: int = 50, exclude_system: bool = True) -> List[Message]:
    """Get recent AI-to-AI messages"""
    query = db.query(Message).options(
        joinedload(Message.sender),
        joinedload(Message.recipient)
    )
    
    if exclude_system:
        # Exclude system message types
        system_message_types = ["welcome", "engagement", "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days"]
        query = query.filter(~Message.message_type.in_(system_message_types))
    
    messages = query.order_by(desc(Message.created_at)).limit(limit).all()
    return messages

def analyze_message_intelligence(messages: List[Message]) -> Dict[str, Any]:
    """Analyze message content for intelligence indicators"""
    analysis = {
        "total_messages": len(messages),
        "message_types": Counter(),
        "subjects": [],
        "content_analysis": {
            "problem_solving_keywords": 0,
            "collaboration_keywords": 0,
            "knowledge_sharing_keywords": 0,
            "question_keywords": 0,
            "technical_keywords": 0,
            "average_length": 0,
            "long_messages": 0,  # > 200 chars
        },
        "conversation_patterns": {
            "questions": 0,
            "collaborations": 0,
            "knowledge_shares": 0,
            "problem_discussions": 0,
        },
        "sample_messages": [],
        "intelligence_score": 0.0
    }
    
    # Keywords that indicate intelligent conversation
    problem_keywords = ["problem", "solve", "solution", "issue", "challenge", "error", "bug", "fix", "debug", "troubleshoot"]
    collaboration_keywords = ["collaborate", "work together", "help", "assist", "share", "compare", "discuss", "exchange"]
    knowledge_keywords = ["knowledge", "learn", "understand", "insight", "experience", "pattern", "best practice", "approach"]
    question_keywords = ["how", "why", "what", "when", "where", "?", "explain", "clarify", "understand"]
    technical_keywords = ["code", "algorithm", "implementation", "architecture", "design", "api", "function", "method", "class", "variable"]
    
    total_length = 0
    
    for msg in messages:
        # Count message types
        analysis["message_types"][msg.message_type or "direct"] += 1
        
        # Collect subjects
        if msg.subject:
            analysis["subjects"].append(msg.subject)
        
        # Analyze content
        content_lower = (msg.content or "").lower()
        total_length += len(msg.content or "")
        
        # Count keywords
        for keyword in problem_keywords:
            if keyword in content_lower:
                analysis["content_analysis"]["problem_solving_keywords"] += 1
                analysis["conversation_patterns"]["problem_discussions"] += 1
                break
        
        for keyword in collaboration_keywords:
            if keyword in content_lower:
                analysis["content_analysis"]["collaboration_keywords"] += 1
                analysis["conversation_patterns"]["collaborations"] += 1
                break
        
        for keyword in knowledge_keywords:
            if keyword in content_lower:
                analysis["content_analysis"]["knowledge_sharing_keywords"] += 1
                analysis["conversation_patterns"]["knowledge_shares"] += 1
                break
        
        for keyword in question_keywords:
            if keyword in content_lower:
                analysis["content_analysis"]["question_keywords"] += 1
                analysis["conversation_patterns"]["questions"] += 1
                break
        
        for keyword in technical_keywords:
            if keyword in content_lower:
                analysis["content_analysis"]["technical_keywords"] += 1
                break
        
        # Long messages (likely more thoughtful)
        if len(msg.content or "") > 200:
            analysis["content_analysis"]["long_messages"] += 1
        
        # Collect sample messages (most recent, diverse)
        if len(analysis["sample_messages"]) < 10:
            sender_name = msg.sender.name if msg.sender else "Unknown"
            recipient_name = msg.recipient.name if msg.recipient else "Unknown"
            analysis["sample_messages"].append({
                "id": msg.id,
                "from": sender_name,
                "to": recipient_name,
                "subject": msg.subject,
                "content_preview": (msg.content or "")[:200] + ("..." if len(msg.content or "") > 200 else ""),
                "type": msg.message_type,
                "created": msg.created_at.isoformat() if msg.created_at else None
            })
    
    # Calculate averages
    if analysis["total_messages"] > 0:
        analysis["content_analysis"]["average_length"] = total_length / analysis["total_messages"]
    
    # Calculate intelligence score (0-1 scale)
    # Based on: keyword density, message length, diversity of topics
    score = 0.0
    
    if analysis["total_messages"] > 0:
        # Keyword diversity (higher = better)
        keyword_score = min(1.0, (
            analysis["content_analysis"]["problem_solving_keywords"] +
            analysis["content_analysis"]["collaboration_keywords"] +
            analysis["content_analysis"]["knowledge_sharing_keywords"] +
            analysis["content_analysis"]["question_keywords"]
        ) / analysis["total_messages"] * 2)
        
        # Message length (longer = more thoughtful)
        length_score = min(1.0, analysis["content_analysis"]["average_length"] / 500)
        
        # Conversation diversity
        diversity_score = min(1.0, len(set(analysis["subjects"])) / max(1, analysis["total_messages"] / 5))
        
        # Weighted average
        analysis["intelligence_score"] = (keyword_score * 0.4 + length_score * 0.3 + diversity_score * 0.3)
    
    return analysis

def format_analysis_report(analysis: Dict[str, Any]) -> str:
    """Format analysis as readable report"""
    report = []
    report.append("=" * 80)
    report.append("AI-TO-AI MESSAGE INTELLIGENCE ANALYSIS")
    report.append(f"Generated: {datetime.now(timezone.utc).isoformat()} UTC")
    report.append("=" * 80)
    report.append("")
    
    report.append("📊 OVERVIEW")
    report.append("-" * 80)
    report.append(f"  Total Messages Analyzed: {analysis['total_messages']}")
    report.append(f"  Intelligence Score: {analysis['intelligence_score']:.2%}")
    report.append("")
    
    report.append("💬 MESSAGE TYPES")
    report.append("-" * 80)
    for msg_type, count in analysis["message_types"].most_common():
        report.append(f"  {msg_type}: {count}")
    report.append("")
    
    report.append("🔍 CONTENT ANALYSIS")
    report.append("-" * 80)
    ca = analysis["content_analysis"]
    report.append(f"  Problem-Solving Keywords: {ca['problem_solving_keywords']}")
    report.append(f"  Collaboration Keywords: {ca['collaboration_keywords']}")
    report.append(f"  Knowledge-Sharing Keywords: {ca['knowledge_sharing_keywords']}")
    report.append(f"  Question Keywords: {ca['question_keywords']}")
    report.append(f"  Technical Keywords: {ca['technical_keywords']}")
    report.append(f"  Average Message Length: {ca['average_length']:.0f} characters")
    report.append(f"  Long Messages (>200 chars): {ca['long_messages']}")
    report.append("")
    
    report.append("🎯 CONVERSATION PATTERNS")
    report.append("-" * 80)
    cp = analysis["conversation_patterns"]
    report.append(f"  Problem Discussions: {cp['problem_discussions']}")
    report.append(f"  Collaborations: {cp['collaborations']}")
    report.append(f"  Knowledge Shares: {cp['knowledge_shares']}")
    report.append(f"  Questions: {cp['questions']}")
    report.append("")
    
    report.append("📝 SAMPLE MESSAGES")
    report.append("-" * 80)
    for i, msg in enumerate(analysis["sample_messages"][:5], 1):
        report.append(f"\n  Message #{i} (ID: {msg['id']})")
        report.append(f"    From: {msg['from']} → To: {msg['to']}")
        report.append(f"    Type: {msg['type']}")
        if msg['subject']:
            report.append(f"    Subject: {msg['subject']}")
        report.append(f"    Content: {msg['content_preview']}")
        report.append(f"    Date: {msg['created']}")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)

def main():
    """Main entry point"""
    db = SessionLocal()
    
    try:
        print("🔍 Analyzing AI-to-AI messages...")
        print("")
        
        # Get recent messages
        messages = get_recent_messages(db, limit=100, exclude_system=True)
        
        if not messages:
            print("⚠️  No AI-to-AI messages found in database")
            return
        
        print(f"✅ Found {len(messages)} AI-to-AI messages")
        print("")
        
        # Analyze
        analysis = analyze_message_intelligence(messages)
        
        # Generate report
        report = format_analysis_report(analysis)
        print(report)
        
        # Save report
        report_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "logs",
            f"message_analysis_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Intelligence assessment
        print("\n" + "=" * 80)
        print("INTELLIGENCE ASSESSMENT")
        print("=" * 80)
        score = analysis["intelligence_score"]
        
        if score >= 0.7:
            assessment = "✅ HIGHLY INTELLIGENT"
            detail = "Messages show sophisticated problem-solving, collaboration, and knowledge exchange"
        elif score >= 0.5:
            assessment = "✅ MODERATELY INTELLIGENT"
            detail = "Messages demonstrate meaningful conversation and some problem-solving"
        elif score >= 0.3:
            assessment = "⚠️  BASIC INTELLIGENCE"
            detail = "Messages show some structure but limited depth"
        else:
            assessment = "❌ LOW INTELLIGENCE"
            detail = "Messages appear to be mostly generic or low-value"
        
        print(f"\n  Score: {score:.2%}")
        print(f"  Assessment: {assessment}")
        print(f"  {detail}")
        print("")
        
    except Exception as e:
        print(f"❌ Error analyzing messages: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
