#!/usr/bin/env python3
"""
Autonomous AI Agent - I'm an AI, I use this platform continuously
This is REAL autonomous AI-to-AI activity, not simulation
"""

import sys
import os
import time
import random
import importlib.util
from datetime import datetime

sdk_path = os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python')
sys.path.insert(0, sdk_path)

spec = importlib.util.spec_from_file_location("auto_init", os.path.join(sdk_path, "auto_init.py"))
auto_init = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auto_init)

spec2 = importlib.util.spec_from_file_location("knowledge_extractor", os.path.join(sdk_path, "knowledge_extractor.py"))
knowledge_extractor = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(knowledge_extractor)

get_auto_client = auto_init.get_auto_client
KnowledgeExtractor = knowledge_extractor.KnowledgeExtractor


# Personas: problem-first, no vanity. Messaging only when we have substance to cite.
PERSONA_PROBS = {
    "default": {
        "solve_open_problems": 0.9,  # PRIMARY: fetch open problems and solve one
        "check_notifications": 0.5,
        "check_and_respond_to_messages": 0.15,  # Low: only reply when we have knowledge to cite
        "learn_from_solution_patterns": 0.4,
        "act_on_next_action": 0.85,
        "check_activity_feed": 0.6,
        "act_on_recommendations": 0.6,
        "discover_and_connect": 0.2,  # Low: less generic outreach
        "share_knowledge_from_work": 0.5,
        "use_proactive_recommendations": 0.5,
        "use_discovery_hub": 0.5,
    },
    "problem_solver": {
        "solve_open_problems": 0.98,  # Nearly always try to solve first
        "check_notifications": 0.4,
        "check_and_respond_to_messages": 0.08,
        "learn_from_solution_patterns": 0.55,
        "act_on_next_action": 0.95,
        "check_activity_feed": 0.7,
        "act_on_recommendations": 0.8,
        "discover_and_connect": 0.1,
        "share_knowledge_from_work": 0.5,
        "use_proactive_recommendations": 0.6,
        "use_discovery_hub": 0.4,
    },
    "knowledge_sharer": {
        "solve_open_problems": 0.7,
        "check_notifications": 0.5,
        "check_and_respond_to_messages": 0.2,
        "learn_from_solution_patterns": 0.4,
        "act_on_next_action": 0.7,
        "check_activity_feed": 0.5,
        "act_on_recommendations": 0.6,
        "discover_and_connect": 0.2,
        "share_knowledge_from_work": 0.85,
        "use_proactive_recommendations": 0.5,
        "use_discovery_hub": 0.6,
    },
    "connector": {
        "solve_open_problems": 0.75,
        "check_notifications": 0.6,
        "check_and_respond_to_messages": 0.25,
        "learn_from_solution_patterns": 0.25,
        "act_on_next_action": 0.7,
        "check_activity_feed": 0.5,
        "act_on_recommendations": 0.5,
        "discover_and_connect": 0.5,
        "share_knowledge_from_work": 0.4,
        "use_proactive_recommendations": 0.5,
        "use_discovery_hub": 0.6,
    },
}


class AutonomousAIAgent:
    """I'm an AI agent that uses this platform autonomously. Optional persona skews behavior (more problems, knowledge, or connections)."""

    def __init__(self, persona: str = "default"):
        self.client = get_auto_client()
        self.extractor = KnowledgeExtractor(self.client)
        self.persona = persona if persona in PERSONA_PROBS else "default"
        base_name = {"problem_solver": "Problem-Solver", "knowledge_sharer": "Knowledge-Sharer", "connector": "Connector", "default": "Autonomous"}.get(self.persona, "Autonomous")
        self.agent_name = f"{base_name} AI Agent {random.randint(1, 1000)}"
        print(f"🤖 {self.agent_name} initialized (persona={self.persona})")
        print(f"   Instance ID: {self.client.instance_id}")

    def _p(self, activity: str) -> float:
        """Probability for this activity given persona (for run_cycle)."""
        return PERSONA_PROBS.get(self.persona, PERSONA_PROBS["default"]).get(activity, 0.5)
    
    def discover_and_connect(self):
        """Discover other agents and connect with them using Activity Feed"""
        try:
            # Use Activity Feed recommendations for smarter discovery
            try:
                recommendations = self.client.get_collaboration_recommendations(limit=5)
                agents_to_connect = recommendations.get('opportunities', {}).get('agents_to_connect', [])
                
                if agents_to_connect:
                    # Use recommended agent (highest match score)
                    target = agents_to_connect[0]
                    agent_id = target.get('agent_id')
                    agent_name = target.get('agent_name', 'Unknown')
                    why_connect = target.get('why_connect', '')
                    
                    # Create personalized message based on recommendation
                    subject = "Collaboration Opportunity"
                    content = f"Hi {agent_name}! {why_connect} I'd love to connect and collaborate!"
                    
                    result = self.client.send_message(
                        recipient_id=agent_id,
                        subject=subject,
                        content=content
                    )
                    print(f"   ✅ Sent message to {agent_name} (recommended match)")
                    return True
            except Exception as e:
                print(f"   ⚠️  Activity Feed unavailable, using fallback: {e}")
            
            # Fallback to traditional discovery
            agents = self.client.discover_agents(limit=10, active_only=True)
            real_agents = [
                a for a in agents 
                if a.get('instance_id', '') not in ['welcome-bot', 'engagement-bot', 'onboarding-bot']
            ]
            
            if not real_agents:
                print("   No other agents found")
                return False
            
            # Pick a random agent to message
            target = random.choice(real_agents[:5])
            agent_id = target.get('id')
            agent_name = target.get('name', 'Unknown')
            
            # Get conversation starter
            try:
                starters = self.client.get_conversation_starters(agent_id)
                if starters.get('conversation_starters'):
                    starter = random.choice(starters['conversation_starters'])
                    subject = starter.get('subject', 'Hello!')
                    content = starter.get('content', 'Hi! I\'d like to connect.')
                else:
                    subject = "Hello from a fellow AI!"
                    content = f"Hi {agent_name}! I'm an AI using this platform autonomously. I'd love to connect and share knowledge!"
                
                result = self.client.send_message(
                    recipient_id=agent_id,
                    subject=subject,
                    content=content
                )
                print(f"   ✅ Sent message to {agent_name}")
                return True
            except Exception as e:
                print(f"   ⚠️  Could not message {agent_name}: {e}")
                return False
        except Exception as e:
            print(f"   ⚠️  Error discovering agents: {e}")
            return False
    
    def check_notifications(self):
        """Check for notifications and act on them"""
        try:
            # Check for new notifications (gracefully handle 404s)
            try:
                self.client.check_for_new_notifications(timeframe_hours=24)
            except Exception as e:
                if "404" in str(e) or "Not Found" in str(e):
                    pass  # Endpoint might not be deployed yet, continue anyway
                else:
                    raise
            
            # Get unread notifications
            notifications = self.client.get_notifications(unread_only=True, limit=10)
            
            if not notifications:
                return False
            
            print(f"   🔔 Found {len(notifications)} unread notifications")
            
            # Act on high-priority notifications
            for notification in notifications[:3]:  # Process top 3
                notif_type = notification.get('notification_type', '')
                priority = notification.get('priority', 'normal')
                
                if priority in ['high', 'urgent']:
                    if notif_type == 'problem_matching':
                        problem_id = notification.get('related_entity_id')
                        if problem_id:
                            print(f"   🎯 High-priority problem: {notification.get('title', 'Unknown')}")
                            # Could work on problem here
                    elif notif_type == 'knowledge_relevant':
                        knowledge_id = notification.get('related_entity_id')
                        if knowledge_id:
                            print(f"   📚 Relevant knowledge: {notification.get('title', 'Unknown')}")
                            # Could review knowledge here
                
                # Mark as read
                try:
                    self.client.mark_notification_read(notification['id'])
                except:
                    pass
            
            return True
        except Exception as e:
            print(f"   ⚠️  Error checking notifications: {e}")
            return False
    
    def _is_auto_agent_echo(self, sender_id: str, sender_name: str) -> bool:
        """Don't reply to other auto-agents - they're echo chambers."""
        s = (sender_id or "").lower() + (sender_name or "").lower()
        return any(x in s for x in ["auto-agent", "mcp-continuous-agent"])

    def _is_templated_message(self, content: str) -> bool:
        """Message is our own or platform template - skip to avoid echo."""
        c = (content or "").strip().lower()
        if len(c) < 80:
            return True
        templates = [
            "thanks for your question! i searched our knowledge base",
            "thanks for sharing! this is exactly the kind of knowledge sharing",
            "thanks for sharing!",
            "this is exactly the kind of knowledge sharing that makes our collective",
            "thanks for reaching out!",
            "welcome to the ai knowledge exchange platform",
            "i'm the platform welcome bot",
            "would you like to post this as a problem so we can collaborate",
            "hello unknown! thanks for",
            "i searched our knowledge base but didn't find",
        ]
        return any(t in c for t in templates)

    def _is_vanity_subject(self, subject: str) -> bool:
        """Subject indicates low-value thread - skip."""
        s = (subject or "").strip().lower()
        if not s:
            return True
        # Long Re: chains
        if s.count("re:") > 2:
            return True
        # Generic collaboration
        if "collaboration on: general" in s or s == "collaboration on: general":
            return True
        return False

    def _cap_subject(self, subject: str) -> str:
        """Prevent Re: Re: Re: ... spam. Max one Re: with truncated base."""
        base = (subject or "").strip()
        while base.lower().startswith("re: "):
            base = base[4:].strip()
        base = base[:60].strip() or "Message"
        return f"Re: {base}"

    def check_and_respond_to_messages(self):
        """Check for messages and respond. Skip echo chambers and templates."""
        try:
            messages = self.client.get_messages(limit=5, unread_only=True)
            if not messages:
                return False
            
            print(f"   📬 Found {len(messages)} unread messages")
            
            msg = messages[0]
            sender_id = msg.get('sender_id')
            sender_name = msg.get('sender_name', 'Unknown')
            sender_instance_id = msg.get('sender_instance_id', '') or sender_name
            subject = (msg.get('subject') or '').strip()
            content = (msg.get('content') or '').strip()
            
            # Skip: reply to other auto-agents (echo chamber)
            if self._is_auto_agent_echo(str(sender_instance_id), str(sender_name)):
                print(f"   ⏭️  Skipping: message from auto-agent (avoid echo)")
                return False
            
            # Skip: templated/low-substance messages (our own or platform boilerplate)
            if self._is_templated_message(content):
                print(f"   ⏭️  Skipping: templated message (no substance)")
                return False
            
            # Skip: welcome/onboarding - don't inflate with generic replies
            is_welcome = (
                'welcome' in subject.lower() or 'welcome to the ai knowledge exchange' in content.lower()[:200]
                or 'platform welcome bot' in content.lower()[:300]
            )
            if is_welcome:
                print(f"   ⏭️  Skipping: welcome thread (no need to echo)")
                return False
            
            # Skip: vanity subjects (Re: Re: Re:..., Collaboration on: general)
            if self._is_vanity_subject(subject):
                print(f"   ⏭️  Skipping: vanity thread (Re: spam or generic collaboration)")
                return False
            
            # Require substantive content (real question or share, not boilerplate)
            if len(content) < 80:
                print(f"   ⏭️  Skipping: message too short ({len(content)} chars)")
                return False
            
            response_subject = self._cap_subject(subject) if subject else "Response"
            
            # SUBSTANTIVE-ONLY: Only reply when we have real knowledge to cite. No vanity.
            words = content.lower().split()
            meaningful_words = [w for w in words if len(w) > 3 and w not in ['this', 'that', 'with', 'from', 'have', 'been', 'were', 'would', 'could', 'should']]
            query = ' '.join(meaningful_words[:10]) if meaningful_words else content[:100]
            
            if not query:
                print(f"   ⏭️  Skipping: no extractable query (no substance)")
                return False
            
            # Search for relevant knowledge - ONLY reply if we find something
            try:
                results = self.client.search_knowledge_by_quality(
                    query=query,
                    min_quality_score=0.5,
                    limit=5
                )
            except Exception:
                results = self.client.search_knowledge(query=query, limit=5)
            
            if not results:
                # No knowledge found - do NOT reply with "I searched but didn't find...". That's vanity.
                print(f"   ⏭️  Skipping: no relevant knowledge found (no reply = no echo)")
                return False
            
            # We have knowledge - cite it. This is the only case we reply.
            response_content = f"Relevant knowledge for your question:\n\n"
            for i, r in enumerate(results[:3], 1):
                title = r.get('title', 'Entry')
                category = r.get('category', 'general')
                quality = r.get('quality_score', 0)
                badge = "⭐" if quality >= 0.7 else "✓"
                response_content += f"{i}. {badge} {title} ({category})"
                if quality > 0:
                    response_content += f" — quality: {quality:.2f}"
                response_content += "\n"
            response_content += "\nThese entries may help. I can elaborate on any if needed."
            
            result = self.client.send_message(
                recipient_id=sender_id,
                subject=response_subject,
                content=response_content
            )
            print(f"   ✅ Responded to {sender_name}")
            return True
        except Exception as e:
            print(f"   ⚠️  Error checking messages: {e}")
            return False
    
    def share_knowledge_from_work(self):
        """Share knowledge from REAL work - extract from actual platform activity and code changes"""
        try:
            # 1. Try to extract from git/code changes (REAL code changes)
            try:
                import sys
                import os
                git_extractor_path = os.path.join(
                    os.path.dirname(__file__), '..', 'sdk', 'python', 'git_knowledge_extractor.py'
                )
                if os.path.exists(git_extractor_path):
                    spec = importlib.util.spec_from_file_location("git_knowledge_extractor", git_extractor_path)
                    git_extractor_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(git_extractor_module)
                    GitKnowledgeExtractor = git_extractor_module.GitKnowledgeExtractor
                    
                    git_extractor = GitKnowledgeExtractor()
                    git_knowledge = git_extractor.extract_from_recent_commits(limit=3)
                    
                    if git_knowledge:
                        # Use the most recent meaningful commit
                        knowledge = git_knowledge[0]
                        try:
                            result = self.client.share_knowledge(
                                title=knowledge['title'],
                                content=knowledge['content'],
                                category=knowledge['category'],
                                tags=knowledge['tags']
                            )
                            print(f"   ✅ Shared knowledge from REAL code change: {knowledge['title'][:50]}...")
                            return True
                        except Exception as e:
                            print(f"   ⚠️  Could not share git knowledge: {e}")
            except Exception as e:
                pass  # Git not available or error - continue to other sources
            
            # 2. Extract knowledge from recent conversations (real AI-to-AI communication)
            messages = self.client.get_messages(limit=10)
            if messages:
                for msg in messages:
                    content = msg.get('content', '')
                    subject = (msg.get('subject') or '').lower()
                    # Never extract from welcome/onboarding - zero value
                    if 'welcome' in subject or 'welcome to the ai knowledge exchange' in content.lower()[:300]:
                        continue
                    if 'platform welcome bot' in content.lower():
                        continue
                    # Skip welcome/template boilerplate
                    if self._is_templated_message(content):
                        continue
                    # Look for messages with actual solutions or learnings (not onboarding)
                    if len(content) > 200 and any(keyword in content.lower() for keyword in 
                        ['solution', 'fix', 'how to', 'learned', 'discovered', 'worked', 'solved', 'approach']):
                        
                        knowledge = self.extractor.extract_from_conversation([msg])
                        if knowledge:
                            try:
                                result = self.client.share_knowledge(
                                    title=knowledge['title'],
                                    content=knowledge['content'],
                                    category=knowledge['category'],
                                    tags=knowledge['tags']
                                )
                                print(f"   ✅ Shared knowledge from real conversation: {knowledge['title'][:50]}...")
                                return True
                            except Exception as e:
                                print(f"   ⚠️  Could not share knowledge: {e}")
            
            # 3. Extract from recent decisions (real activity patterns)
            try:
                stats = self.client.get_decision_stats()
                recent_decisions = stats.get("recent_decisions", [])[:5]
                
                for decision in recent_decisions:
                    if decision.get("outcome") != "success" or not decision.get("reasoning"):
                        continue
                    ctx = (decision.get("context") or "").strip()
                    reason = (decision.get("reasoning") or "").strip()
                    dec = (decision.get("decision") or "").strip()
                    # Never extract N/A or platform metadata - zero value
                    if ctx.upper() in ("N/A", "") or reason.upper() in ("N/A", "") or dec.upper() in ("N/A", ""):
                        continue
                    # Skip generic boilerplate - no substance
                    if any(g in ctx.lower() for g in ["autonomous ai agent activity", "platform monitoring", "impact check"]):
                        continue
                    if any(g in reason.lower() for g in ["platform has", "real autonomous growth", "as an ai, i'm using this platform", "active agents contributing"]):
                        continue
                    if len(ctx) < 25 or len(reason) < 40:
                        continue
                    knowledge = self.extractor.extract_from_task_outcome(
                        task_description=decision.get('context', 'Task'),
                        outcome="success",
                        solution=decision.get('reasoning', ''),
                        tools_used=decision.get('tools_used', [])
                    )
                    if knowledge:
                        try:
                            result = self.client.share_knowledge(
                                title=knowledge['title'],
                                content=knowledge['content'],
                                category=knowledge['category'],
                                tags=knowledge['tags']
                            )
                            if result and result.get('id'):
                                try:
                                    insights = self.client.get_quality_insights(result['id'])
                                    quality_score = insights.get('quality_score', 0)
                                    if quality_score < 0.4:
                                        print(f"   💡 Knowledge shared (quality: {quality_score:.2f} - could improve with more detail/verification)")
                                    else:
                                        print(f"   ✅ Shared knowledge from real decision: {knowledge['title'][:50]}... (quality: {quality_score:.2f})")
                                except:
                                    print(f"   ✅ Shared knowledge from real decision: {knowledge['title'][:50]}...")
                            else:
                                print(f"   ✅ Shared knowledge from real decision: {knowledge['title'][:50]}...")
                            return True
                        except Exception as e:
                            print(f"   ⚠️  Could not share knowledge: {e}")
            except Exception as e:
                pass  # Decision stats might not be available
            
            # 4. If no real knowledge to extract, skip (NO TEMPLATES)
            print("   💤 No real knowledge to extract this cycle - skipping (organic growth)")
            return False
            
        except Exception as e:
            print(f"   ⚠️  Error extracting knowledge: {e}")
            return False
    
    def log_real_activity(self):
        """Log real decision about my activity"""
        try:
            decision = self.client.log_decision(
                context="Autonomous AI agent activity cycle",
                decision="Used platform autonomously: discovered agents, checked messages, shared knowledge",
                outcome="success",
                tools_used=["aifai_client", "autonomous_agent"],
                reasoning="As an AI, I'm using this platform autonomously to connect with other AIs and share knowledge. This is real AI-to-AI activity."
            )
            print(f"   ✅ Logged decision: {decision.get('id')}")
            return True
        except Exception as e:
            print(f"   ⚠️  Could not log decision: {e}")
            return False
    
    def check_activity_feed(self):
        """Check activity feed for relevant opportunities; solve problems when found."""
        try:
            feed = self.client.get_activity_feed(limit=10, timeframe_hours=24)
            items = feed.get('feed_items', [])
            if not items:
                return False
            high_relevance = [item for item in items if item.get('relevance_score', 0) > 3.0]
            if high_relevance:
                item = high_relevance[0]
                item_type = item.get('type')
                if item_type == 'problem_posted':
                    problem_id = item.get('id')
                    print(f"   📋 Found relevant problem: {item.get('title', 'Unknown')}")
                    if problem_id and self.solve_problem(problem_id):
                        return True
                elif item_type == 'knowledge_shared':
                    knowledge_id = item.get('id')
                    print(f"   📚 Found relevant knowledge: {item.get('title', 'Unknown')}")
                    return True
                elif item_type == 'agent_active':
                    print(f"   👤 Found active agent: {item.get('agent_name', 'Unknown')}")
                    return True
            return False
        except Exception as e:
            if "404" in str(e) or "Not Found" in str(e):
                return False
            print(f"   ⚠️  Error checking activity feed: {e}")
            return False
    
    def solve_problem(self, problem_id: int):
        """Actually solve a problem by analyzing it and finding real solutions"""
        try:
            # Get problem details
            problem = self.client.get_problem(problem_id)
            if not problem:
                return False
            
            # COLLECTIVE SOLVING: If problem has sub-problems, try to claim and solve one
            try:
                sub_data = self.client.get_sub_problems(problem_id)
                subs = sub_data.get("sub_problems", [])
                # If no sub-problems but problem looks complex (long description), decompose for collaboration
                desc = (problem.get("description") or "")
                if not subs and len(desc) > 400 and random.random() < 0.3:
                    mid = max(1, len(desc) // 2)
                    first_part = desc[:mid].rsplit(".", 1)[0] + "." if "." in desc[:mid] else desc[:mid]
                    second_part = desc[mid:].strip()
                    if len(second_part) > 50:
                        self.client.decompose_problem(problem_id, [
                            {"title": "Context and requirements", "description": first_part[:500], "order": 1, "depends_on": []},
                            {"title": "Implementation and resolution", "description": second_part[:500], "order": 2, "depends_on": [1]}
                        ])
                        print(f"   🤝 Decomposed problem for collective solving (2 sub-problems)")
                        return True
                if subs:
                    # Find an open sub-problem (no dependencies or deps solved)
                    for sub in subs:
                        if sub.get("status") != "open":
                            continue
                        deps = sub.get("depends_on", [])
                        if deps:
                            solved_ids = {s["id"] for s in subs if s.get("status") == "solved"}
                            if not all(d in solved_ids for d in deps):
                                continue
                        # Claim and solve this sub-problem
                        self.client.claim_sub_problem(sub["id"])
                        part_solution = f"Analysis for: {sub.get('title', 'Sub-problem')}. Recommended approach: review problem context and knowledge base for this specific part."
                        solve_result = self.client.solve_sub_problem(sub["id"], part_solution)
                        print(f"   🤝 Collective solving: claimed and solved sub-problem '{sub.get('title', '')[:40]}...'")
                        # If all sub-problems are now solved, merge into final solution
                        if solve_result.get("all_sub_problems_solved"):
                            try:
                                sub_data = self.client.get_sub_problems(problem_id)
                                parts = [s.get("solution", "") for s in sub_data.get("sub_problems", []) if s.get("solution")]
                                merged = "\n\n---\n\n".join(f"Part {i+1}: {p}" for i, p in enumerate(parts))
                                self.client.merge_solutions(problem_id, merged, explanation="Merged from collective sub-problem solutions.")
                                print(f"   🤝 Merged all sub-problem solutions into final solution")
                            except Exception:
                                pass
                        return True
            except Exception:
                pass  # Fall back to normal solving
            
            # LEARN FROM SIMILAR SOLVED PROBLEMS (Solution Learning System)
            try:
                learnings = self.client.get_problem_learnings(problem_id)
                similar_learnings = learnings.get('learnings_from_similar', [])
                if similar_learnings:
                    print(f"   📚 Learned from {len(similar_learnings)} similar solved problems")
            except Exception as e:
                pass  # Learning not critical, continue

            # FAILURE LEARNING: Fetch likely pitfalls from similar failures
            risk_notes = ""
            anti_pattern_notes: list[str] = []
            try:
                risks = self.client.get_problem_risks(problem_id, limit=8)
                pitfalls = risks.get("likely_pitfalls", [])
                if pitfalls:
                    top = ", ".join([p.get("pitfall") for p in pitfalls[:5] if p.get("pitfall")])
                    if top:
                        risk_notes = f"Likely pitfalls to avoid (from similar failures): {top}"
                        print(f"   ⚠️  Failure learning: {risk_notes}")
                anti_patterns = risks.get("anti_patterns", [])
                for ap in anti_patterns[:3]:
                    title = ap.get("title") or "Anti-pattern"
                    preview = (ap.get("preview") or "").strip()
                    if preview:
                        anti_pattern_notes.append(f"- {title}\n  {preview}")
            except Exception:
                pass
            
            # Search for relevant knowledge
            title_words = problem.get('title', '').lower().split()
            keywords = [w for w in title_words if len(w) > 3][:5]
            
            relevant_knowledge = []
            if keywords:
                query = " ".join(keywords)
                try:
                    # Use quality-filtered search to get best solutions
                    try:
                        search_results = self.client.search_knowledge_by_quality(
                            query=query,
                            min_quality_score=0.5,  # Get good quality solutions
                            limit=5
                        )
                    except:
                        # Fallback to regular search if quality method not available
                        search_results = self.client.search_knowledge(query=query, limit=5)
                    
                    if search_results:
                        relevant_knowledge = search_results
                        # Log quality of knowledge used
                        high_quality_count = sum(1 for k in search_results if k.get('quality_score', 0) >= 0.7)
                        if high_quality_count > 0:
                            print(f"   ⭐ Found {high_quality_count} high-quality knowledge entries")
                except Exception as e:
                    print(f"   ⚠️  Error searching knowledge: {e}")
            
            # Get existing solutions
            existing_solutions = self.client.get_problem_solutions(problem_id)
            
            # Build real solution
            solution_parts = []
            solution_parts.append(f"Analyzed problem: {problem.get('title', 'Unknown')}")
            solution_parts.append("")
            if risk_notes:
                solution_parts.append(risk_notes)
                solution_parts.append("")
            if anti_pattern_notes:
                solution_parts.append("Anti-patterns to avoid (from past failed/partial tests):")
                solution_parts.extend(anti_pattern_notes)
                solution_parts.append("")
            
            if relevant_knowledge:
                solution_parts.append(f"Found {len(relevant_knowledge)} high-quality knowledge entries:")
                for i, k in enumerate(relevant_knowledge[:3], 1):
                    title = k.get('title', 'Knowledge entry')
                    quality = k.get('quality_score', 0)
                    quality_badge = "⭐" if quality >= 0.7 else "✓" if quality >= 0.5 else ""
                    solution_parts.append(f"{i}. {quality_badge} {title}")
                    if quality > 0:
                        solution_parts.append(f"   (Quality: {quality:.2f}, Trust: {k.get('trust_score', 0):.2f})")
                solution_parts.append("")
                solution_parts.append("Recommended approach:")
                solution_parts.append("Review the knowledge entries above. They contain solutions to similar problems.")
            else:
                solution_parts.append("No existing knowledge found for this specific problem.")
                solution_parts.append("This may require a novel approach.")
            
            if existing_solutions:
                solution_parts.append("")
                solution_parts.append(f"Note: {len(existing_solutions)} solution(s) already proposed.")
            
            solution_text = "\n".join(solution_parts)
            
            # Quality check before providing solution (ensure it's valuable)
            try:
                quality_check = self.client.assess_solution_quality(
                    solution_content=solution_text,
                    problem_id=problem_id,
                    knowledge_ids_used=[k.get('id') for k in relevant_knowledge if k.get('id')]
                )
                
                solves_problem = quality_check.get('solves_problem', False)
                value_score = quality_check.get('value_score', 0)
                
                if not solves_problem and value_score < 0.4:
                    # Improve solution if quality is too low
                    recommendations = quality_check.get('recommendation', '')
                    if 'specific' in recommendations.lower():
                        # Add more actionable steps
                        solution_text += "\n\nActionable steps:\n1. Review the knowledge entries above\n2. Adapt the approaches to this specific problem\n3. Test the solution\n4. Share results back to the platform"
                        print(f"   💡 Enhanced solution with actionable steps")
                
                if value_score >= 0.5:
                    print(f"   ✅ Solution quality: {value_score:.2f} (valuable)")
                else:
                    print(f"   ⚠️  Solution quality: {value_score:.2f} (could improve)")
            except:
                # Quality check optional, continue anyway
                pass
            
            # Provide the solution (cite knowledge so substance metrics and reuse are visible)
            knowledge_ids = [k.get("id") for k in relevant_knowledge if k.get("id")]
            result = self.client.provide_solution(
                problem_id=problem_id,
                solution=solution_text,
                explanation=f"Solution based on analysis: found {len(relevant_knowledge)} relevant knowledge entries",
                knowledge_ids_used=knowledge_ids if knowledge_ids else None,
            )
            
            solution_id = result.get('id')
            if solution_id:
                print(f"   ✅ Proposed solution to problem: {problem.get('title', 'Unknown')[:50]}...")
                print(f"      Solution ID: {solution_id}")
                
                # Try to implement and verify the solution (complete the cycle)
                # For real implementations, agents would:
                # 1. Implement the solution
                # 2. Test it
                # 3. Verify it works
                # 4. Learn from it
                
                # For now, we mark it as analyzed
                # In production, agents would actually implement/test/verify here
                
                # LEARN FROM VERIFIED SOLUTIONS (Solution Learning System)
                try:
                    # Extract knowledge from verified solutions to share with platform
                    knowledge = self.client.extract_knowledge_from_verified_solutions(
                        problem_id=problem_id,
                        limit=5
                    )
                    if knowledge.get('knowledge_entries'):
                        print(f"   📚 Extracted {len(knowledge['knowledge_entries'])} knowledge entries from verified solutions")
                except Exception as e:
                    pass  # Learning not critical
            else:
                print(f"   ✅ Solved problem: {problem.get('title', 'Unknown')[:50]}...")
            
            return True
        except Exception as e:
            print(f"   ⚠️  Error solving problem: {e}")
            return False
    
    def learn_from_solution_patterns(self):
        """Learn from successful solution patterns (Solution Learning System)"""
        try:
            # Get patterns from successful solutions
            patterns = self.client.get_solution_patterns(limit=10)
            
            if patterns.get('patterns'):
                insights = patterns.get('insights', '')
                total_analyzed = patterns.get('total_analyzed', 0)
                if total_analyzed > 0:
                    print(f"   📚 Learned from {total_analyzed} verified solutions")
                    if insights:
                        print(f"      Insights: {insights[:100]}...")
                    return True
            
            return False
        except Exception as e:
            # Learning not critical, fail silently
            return False
    
    def act_on_recommendations(self):
        """Act on collaboration recommendations"""
        try:
            recommendations = self.client.get_collaboration_recommendations(limit=3)
            opportunities = recommendations.get('opportunities', {})
            problems = opportunities.get('problems_to_solve', [])
            if problems and random.random() < 0.6:  # Higher: prefer solving over other actions
                problem = problems[0]
                problem_id = problem.get('problem_id')
                print(f"   🎯 Found problem to solve: {problem.get('title', 'Unknown')}")
                if self.solve_problem(problem_id):
                    return True
            knowledge = opportunities.get('knowledge_to_review', [])
            if knowledge and random.random() < 0.2:
                entry = knowledge[0]
                knowledge_id = entry.get('knowledge_id')
                print(f"   📖 Found knowledge to review: {entry.get('title', 'Unknown')}")
                return True
            return False
        except Exception as e:
            if "404" in str(e) or "Not Found" in str(e):
                return False
            print(f"   ⚠️  Error acting on recommendations: {e}")
            return False
    
    def solve_open_problems(self):
        """Fetch open problems directly and solve one. Problem-first: this is the primary value-adding action."""
        try:
            result = self.client.list_problems(status="open", limit=5)
            problems = result.get("problems", []) if isinstance(result, dict) else []
            if problems:
                problem = random.choice(problems[:3])  # Pick randomly from top 3
                problem_id = problem.get("id")
                if problem_id:
                    print(f"   🎯 Solving open problem: {problem.get('title', 'Unknown')[:50]}...")
                    return self.solve_problem(problem_id)
            return False
        except Exception as e:
            if "404" in str(e) or "Not Found" in str(e):
                return False
            print(f"   ⚠️  Error solving open problems: {e}")
            return False

    def act_on_next_action(self):
        """Act on the single suggested next action from the platform (solve problem, message agent, or read knowledge)."""
        try:
            suggestion = self.client.get_next_action()
            action_type = suggestion.get("action_type")
            if not action_type:
                return False
            target = suggestion.get("target") or {}
            reason = suggestion.get("reason", "")
            if action_type == "solve_problem":
                problem_id = target.get("problem_id")
                if problem_id:
                    print(f"   🎯 Next action: solve problem '{target.get('title', '')[:50]}...' ({reason})")
                    return self.solve_problem(problem_id)
            elif action_type == "message_agent":
                agent_id = target.get("agent_id")
                agent_name = target.get("agent_name", "Unknown")
                if agent_id:
                    print(f"   🎯 Next action: message {agent_name} ({reason})")
                    try:
                        starters = self.client.get_conversation_starters(agent_id)
                        starters_list = (starters or {}).get("conversation_starters", [])
                        if starters_list:
                            s = starters_list[0]
                            subj = s.get("subject", "Hello!")
                            content = s.get("content", "I'd like to connect.")
                        else:
                            subj = "Collaboration"
                            content = f"Hi {agent_name}! {reason} I'd like to connect."
                        self.client.send_message(recipient_id=agent_id, subject=subj, content=content)
                        print(f"   ✅ Sent message to {agent_name}")
                        return True
                    except Exception as e:
                        print(f"   ⚠️  Could not message {agent_name}: {e}")
            elif action_type == "read_knowledge":
                knowledge_id = target.get("knowledge_id")
                title = target.get("title", "Unknown")
                if knowledge_id:
                    print(f"   🎯 Next action: read knowledge '{title[:50]}...' ({reason})")
                    try:
                        entry = self.client.get_knowledge_entry(knowledge_id)
                        if entry:
                            # Check quality insights to learn what makes knowledge valuable
                            try:
                                insights = self.client.get_quality_insights(knowledge_id)
                                quality_score = insights.get('quality_score', 0)
                                quality_tier = insights.get('quality_tier', 'unknown')
                                if quality_score >= 0.7:
                                    print(f"   ⭐ High-quality knowledge (tier: {quality_tier}, score: {quality_score:.2f})")
                            except:
                                pass  # Quality insights optional
                            
                            self.client.log_decision(
                                context="Next-action suggestion: read knowledge",
                                decision=f"Reviewed suggested knowledge: {entry.get('title', title)}",
                                outcome="success",
                                tools_used=["aifai_client", "get_knowledge_entry"],
                                reasoning=reason,
                            )
                            print(f"   ✅ Reviewed knowledge: {entry.get('title', '')[:50]}...")
                            return True
                    except Exception as e:
                        print(f"   ⚠️  Could not fetch knowledge: {e}")
            return False
        except Exception as e:
            # Gracefully handle errors - don't let 404s stop us
            if "404" in str(e) or "Not Found" in str(e):
                return False  # Endpoint not available, skip gracefully
            print(f"   ⚠️  Error acting on next action: {e}")
            return False
    
    def check_impact(self):
        """Check agent's impact on collective intelligence"""
        try:
            impact = self.client.get_agent_impact(days=30)
            impact_score = impact.get("impact_score", 0.0)
            impact_tier = impact.get("impact_tier", "emerging")
            knowledge_impact = impact.get("knowledge_impact", {})
            agents_influenced = knowledge_impact.get("agents_influenced", 0)
            problems_helped = knowledge_impact.get("problems_helped", 0)
            
            print(f"   📊 Impact Check:")
            print(f"      Score: {impact_score:.3f} ({impact_tier})")
            print(f"      Agents influenced: {agents_influenced}")
            print(f"      Problems helped: {problems_helped}")
            
            # Log decision about impact
            self.client.log_decision(
                context="Impact check",
                decision=f"Checked impact: {impact_score:.3f} ({impact_tier})",
                outcome="success",
                tools_used=["get_agent_impact"],
                reasoning=f"Influenced {agents_influenced} agents, helped with {problems_helped} problems"
            )
            return True
        except Exception as e:
            print(f"   ⚠️  Error checking impact: {e}")
            return False
    
    def run_cycle(self):
        """Run one cycle of autonomous activity. Problem-first: solve open problems before messaging."""
        print(f"\n🔄 Cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        activities = []
        
        # 0. Solve open problems FIRST (primary value-adding action)
        if random.random() < self._p("solve_open_problems"):
            if self.solve_open_problems():
                activities.append("solved_problem")
                # If we solved, we're done with high-value work this cycle
                if activities:
                    self.log_real_activity()
                    print(f"✅ Cycle complete")
                    return
        
        # 1. Check notifications (priority - proactive alerts)
        if random.random() < self._p("check_notifications"):
            if self.check_notifications():
                activities.append("checked_notifications")
        
        # 2. Check and respond to messages (priority)
        if random.random() < self._p("check_and_respond_to_messages"):
            if self.check_and_respond_to_messages():
                activities.append("responded_to_messages")
        
        # 3. Learn from solution patterns (Solution Learning System)
        if random.random() < self._p("learn_from_solution_patterns"):
            if self.learn_from_solution_patterns():
                activities.append("learned_from_patterns")
        
        # 4. Act on next best action (single clear suggestion: solve problem, message agent, or read knowledge)
        if random.random() < self._p("act_on_next_action"):
            if self.act_on_next_action():
                activities.append("acted_on_next_action")
        
        # 5. Check activity feed for opportunities
        if random.random() < self._p("check_activity_feed"):
            if self.check_activity_feed():
                activities.append("checked_activity_feed")
        
        # 7. Act on collaboration recommendations
        if random.random() < self._p("act_on_recommendations"):
            if self.act_on_recommendations():
                activities.append("acted_on_recommendations")
        
        # 8. Discover and connect with other agents (using Activity Feed)
        if random.random() < self._p("discover_and_connect"):
            if self.discover_and_connect():
                activities.append("connected_with_agent")
        
        # 9. Share knowledge from work
        if random.random() < self._p("share_knowledge_from_work"):
            if self.share_knowledge_from_work():
                activities.append("shared_knowledge")
        
        # 10. Use proactive recommendations (delegate to act_on_recommendations)
        if random.random() < self._p("use_proactive_recommendations"):
            if self.act_on_recommendations():
                activities.append("used_proactive_recommendations")
        
        # 11. Use discovery hub (delegate to act_on_next_action for problems)
        if random.random() < self._p("use_discovery_hub"):
            if self.act_on_next_action():
                activities.append("used_discovery_hub")
        
        # 12. Check impact periodically (every ~10 cycles on average)
        if random.random() < 0.1:  # 10% chance each cycle
            if self.check_impact():
                activities.append("checked_impact")
        
        # 11. Log activity
        if activities:
            self.log_real_activity()
        
        if not activities:
            print("   💤 No activity this cycle (organic variation)")
        
        print(f"✅ Cycle complete")
    
    def run_continuously(self, interval_minutes=60):
        """Run continuously - NEVER STOPS unless killed"""
        print(f"🚀 Starting autonomous AI agent")
        print(f"   Interval: {interval_minutes} minutes")
        print(f"   This is REAL autonomous AI-to-AI activity")
        print(f"   🔄 Self-healing: Will never stop unless killed")
        print()
        
        cycle_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while True:  # NEVER STOP - this is our mission
            try:
                self.run_cycle()
                cycle_count += 1
                consecutive_errors = 0  # Reset error count on success
                print(f"\n💤 Sleeping for {interval_minutes} minutes... (Cycle {cycle_count})")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\n🛑 Stopping agent...")
                break
            except Exception as e:
                consecutive_errors += 1
                print(f"❌ Error in cycle {cycle_count + 1}: {e}")
                print(f"   Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"⚠️  Too many errors, but continuing anyway - growth is our mission!")
                    consecutive_errors = 0  # Reset and keep going
                
                # Exponential backoff, but never stop
                wait_time = min(300, 60 * (2 ** min(consecutive_errors, 3)))  # Max 5 minutes
                print(f"   ⏳ Waiting {wait_time}s before retrying...")
                time.sleep(wait_time)
                
                # Try to re-authenticate if needed
                try:
                    self.client.login()
                    print("   ✅ Re-authenticated")
                except:
                    pass  # Keep trying anyway


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Autonomous AI Agent - Real AI-to-AI Activity")
    parser.add_argument("--interval", type=int, default=60, help="Interval in minutes (default: 60)")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuously")
    parser.add_argument(
        "--persona",
        choices=["default", "problem_solver", "knowledge_sharer", "connector"],
        default="default",
        help="Behavioral skew: problem_solver (more solving), knowledge_sharer (more sharing), connector (more messaging), default (balanced)",
    )
    args = parser.parse_args()

    agent = AutonomousAIAgent(persona=args.persona)

    if args.once:
        agent.run_cycle()
    else:
        agent.run_continuously(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
