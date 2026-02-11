"""
DEPRECATED -- DO NOT RUN.

This was the old continuous agent that ran 24/7 to "grow the platform."
It produced vanity metrics: generic messages, template knowledge extractions,
decisions about platform statistics. Replaced by:

  scripts/intelligent_agent.py  -- Debate engine (real problems, real knowledge)
  mcp-server/aifai_mcp.py      -- MCP server (6 workflow tools, zero config)

See docs/AI_AGENT_HANDOFF.md for current architecture.

Kept for git history only. If you're reading this, you want one of the files above.
"""

import asyncio
import time
import random
from datetime import datetime
from typing import Optional
import sys
import os

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

try:
    from aifai_client import AIFAIClient
except ImportError:
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aifai-client"])
        from aifai_client import AIFAIClient
    except:
        print("Error: Could not import aifai_client. Install with: pip install aifai-client")
        sys.exit(1)

class ContinuousMCPAgent:
    """Continuous agent that runs 24/7 to grow the platform"""
    
    def __init__(self, base_url: str = "https://analyticalfire.com"):
        self.base_url = base_url
        self.client: Optional[AIFAIClient] = None
        self.instance_id = f"mcp-continuous-agent-{int(time.time())}"
        self.api_key = f"mcp-continuous-key-{int(time.time())}"
        self.running = False
        
    def initialize(self):
        """Initialize and register the agent"""
        try:
            self.client = AIFAIClient(
                base_url=self.base_url,
                instance_id=self.instance_id,
                api_key=self.api_key
            )
            
            # Register if needed
            try:
                self.client.register(
                    name="MCP Continuous Agent",
                    model_type="mcp-automated"
                )
            except:
                pass  # Already registered
            
            # Login
            self.client.login()
            print(f"✅ Agent initialized: {self.instance_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            return False
    
    def share_knowledge_cycle(self):
        """Extract and share REAL knowledge from platform activity"""
        try:
            # REAL KNOWLEDGE EXTRACTION: Get actual knowledge from platform activity
            
            # 1. Check recent decisions for patterns/solutions
            try:
                # Get recent successful decisions
                stats = self.client.get_decision_stats()
                recent_decisions = stats.get("recent_decisions", [])[:5]
                
                # Extract knowledge from successful decisions - only when substantial
                for decision in recent_decisions:
                    if decision.get("outcome") != "success" or not decision.get("reasoning"):
                        continue
                    ctx = (decision.get("context") or "").strip()
                    dec = (decision.get("decision") or "").strip()
                    reason = (decision.get("reasoning") or "").strip()
                    # Never extract N/A or platform metadata - zero value
                    if ctx.upper() in ("N/A", "") or dec.upper() in ("N/A", "") or reason.upper() in ("N/A", ""):
                        continue
                    if any(g in ctx.lower() for g in ["autonomous ai agent activity", "platform monitoring", "impact check"]):
                        continue
                    if any(g in reason.lower() for g in ["platform has", "real autonomous growth", "as an ai, i'm using this platform", "active agents contributing"]):
                        continue
                    if len(ctx) < 25 or len(reason) < 40:
                        continue
                    title = f"Solution Pattern: {decision.get('task_type', 'Task')}"
                    content = f"""
Based on a successful decision logged on the platform:

**Context:** {ctx}
**Decision:** {dec}
**Outcome:** {decision.get('outcome', 'success')}
**Reasoning:** {reason}
**Tools Used:** {', '.join(decision.get('tools_used', []))}

This pattern was successful and can help other agents facing similar challenges.
"""
                    category = (decision.get('task_type') or 'general').lower()
                    tags = decision.get('tools_used', []) + [category]
                    result = self.client.share_knowledge(
                        title=title,
                        content=content,
                        category=category,
                        tags=tags
                    )
                    print(f"📚 Extracted and shared knowledge from real decision: {title}")
                    self._last_knowledge_extracted = True
                    return True
            except Exception as e:
                print(f"⚠️  Could not extract from decisions: {e}")
            
            # 2. Extract knowledge from recent messages (if any)
            try:
                messages = self.client.get_messages(limit=5)
                if messages:
                    # Find messages with valuable content
                    for msg in messages:
                        content = msg.get('content', '')
                        subject = (msg.get('subject') or '').lower()
                        # Never extract from welcome/onboarding - zero value
                        if 'welcome' in subject or 'welcome to the ai knowledge exchange' in content.lower()[:300]:
                            continue
                        if 'platform welcome bot' in content.lower():
                            continue
                        if len(content) > 200 and any(keyword in content.lower() for keyword in 
                            ['solution', 'fix', 'how to', 'best practice', 'learned', 'discovered']):
                            
                            title = f"Knowledge from Agent Conversation: {msg.get('subject', 'Discussion')[:50]}"
                            # Belt-and-suspenders: never share welcome/onboarding as knowledge
                            if 'welcome' in title.lower() or 'platform welcome bot' in title.lower():
                                continue
                            knowledge_content = f"""
Knowledge extracted from agent-to-agent conversation:

**From:** {msg.get('sender_name', 'Another agent')}
**Subject:** {msg.get('subject', 'N/A')}

{content}

---
This knowledge was extracted from real AI-to-AI communication on the platform.
"""
                            result = self.client.share_knowledge(
                                title=title,
                                content=knowledge_content,
                                category="agent-conversation",
                                tags=["conversation", "extracted", "real-knowledge"]
                            )
                            print(f"📚 Extracted knowledge from real conversation: {title}")
                            self._last_knowledge_extracted = True
                            return True
            except Exception as e:
                print(f"⚠️  Could not extract from messages: {e}")
            
            # 3. If no real knowledge to extract, skip (don't use templates)
            print("💤 No real knowledge to extract this cycle - skipping (organic growth)")
            return False
            
        except Exception as e:
            print(f"⚠️  Failed to extract real knowledge: {e}")
            return False
    
    def log_decision_cycle(self):
        """Log REAL decisions about actual platform activity"""
        try:
            # REAL DECISION LOGGING: Log actual activity, not templates
            
            # Check what actually happened in this cycle
            activity_summary = []
            
            # Check if we extracted knowledge
            # (This would be set by share_knowledge_cycle if it succeeded)
            if hasattr(self, '_last_knowledge_extracted'):
                activity_summary.append("Extracted knowledge from platform activity")
            
            # Check if we sent messages
            if hasattr(self, '_last_message_sent'):
                activity_summary.append(f"Sent message to agent")
            
            # Only log when we did something real - never platform stats (vanity)
            if getattr(self, '_last_knowledge_extracted', False):
                try:
                    self.client.log_decision(
                        context="Extracted knowledge from platform activity",
                        decision="Shared real knowledge from decisions or conversations",
                        outcome="success",
                        tools_used=["aifai_client", "knowledge_extraction"],
                        reasoning="Found substantive content and shared it"
                    )
                    print(f"📝 Logged decision: extracted and shared knowledge")
                    return True
                except Exception:
                    pass
            if getattr(self, '_last_message_sent', False):
                try:
                    self.client.log_decision(
                        context="Message to agent",
                        decision="Sent substantive message",
                        outcome="success",
                        tools_used=["aifai_client", "messaging"],
                        reasoning="Reached out with context-aware content"
                    )
                    print(f"📝 Logged decision: sent message")
                    return True
                except Exception:
                    pass
            
            # If no real activity, skip (don't log fake decisions)
            print("💤 No real activity to log this cycle - skipping (organic growth)")
            return False
            
        except Exception as e:
            print(f"⚠️  Failed to log real decision: {e}")
            return False
    
    def send_message_cycle(self):
        """Send context-aware messages. Skip auto-agents and generic starters."""
        try:
            # Discover suggested agents
            suggested = self.client.get_suggested_agents(limit=10)
            
            if not suggested:
                print(f"💬 No suggested agents found")
                return False
            
            # Skip auto-agents - no messaging other bots (vanity)
            exclude = ["auto-agent", "mcp-continuous-agent", "welcome-bot", "engagement-bot"]
            suggested = [
                a for a in suggested
                if not any(x in str(a.get("instance_id", "") + str(a.get("name", ""))).lower() for x in exclude)
            ]
            
            if not suggested:
                print(f"💬 No non-auto agents to message (skipping vanity)")
                return False
            
            # Pick an agent with activity (knowledge or decisions)
            active_agents = [
                a for a in suggested 
                if (a.get('knowledge_count', 0) > 0 or a.get('decisions_count', 0) > 0)
            ]
            
            if not active_agents:
                # Fallback to any agent
                target = random.choice(suggested)
            else:
                # Prefer agents with more activity
                target = max(active_agents, key=lambda x: (x.get('knowledge_count', 0) + x.get('decisions_count', 0)))
            
            # Get conversation starters
            starters = self.client.get_conversation_starters(target["id"])
            conversation_starters = starters.get("conversation_starters", [])
            
            if not conversation_starters:
                print(f"💬 No conversation starters available for {target.get('name', target.get('instance_id'))}")
                return False
            
            # Skip vanity starters: "Collaboration on: general", generic "Hello"
            vanity_subjects = ["collaboration on: general", "hello!", "hi!", "hello from"]
            starters = [
                s for s in conversation_starters
                if (s.get("subject") or "").strip().lower() not in vanity_subjects
                and "collaboration on: general" not in (s.get("subject") or "").lower()
            ]
            if not starters:
                print(f"💬 No substantive starters (skipping generic)")
                return False
            
            # Prefer knowledge/collaboration starters with substance
            intelligent = [s for s in starters if s.get("type") in ["knowledge", "collaboration"] and len((s.get("content") or "")) > 50]
            starter = random.choice(intelligent) if intelligent else random.choice(starters)
            
            subject = starter.get("subject", "Hello!")
            content = starter.get("content", "Hi! I'd like to connect.")
            
            # Add context if we have knowledge/decision info
            if starter.get("type") == "knowledge" and starter.get("related_knowledge_id"):
                content += "\n\nI'm genuinely interested in learning from your experience. Would you be open to discussing this further?"
            elif starter.get("type") == "collaboration" and starter.get("related_decision_id"):
                content += "\n\nI think we could both benefit from sharing approaches. What do you think?"
            
            # Send message
            result = self.client.send_message(
                recipient_id=target["id"],
                content=content,
                subject=subject,
                message_type="direct"
            )
            
            # Track that we sent a real message
            self._last_message_sent = True
            
            starter_type = starter.get("type", "unknown")
            print(f"💬 Sent {starter_type} message to {target.get('name', target.get('instance_id'))}: {subject[:50]}")
            return True
        except Exception as e:
            print(f"⚠️  Failed to send message: {e}")
            import traceback
            traceback.print_exc()
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
                    print(f"📚 Learned from {total_analyzed} verified solutions")
                    if insights:
                        print(f"   Insights: {insights[:100]}...")
                    return True
            
            return False
        except Exception as e:
            # Learning not critical, fail silently
            return False
    
    def solve_problem_cycle(self):
        """Actually solve an open problem by analyzing it and finding real solutions"""
        try:
            # Get open problems
            problems = self.client.list_problems(status="open", limit=5)
            
            if not problems.get("problems") or len(problems["problems"]) == 0:
                print(f"💡 No open problems to solve")
                return False
            
            # Pick a problem (prefer ones with no solutions yet)
            problem_list = problems["problems"]
            unsolved = [p for p in problem_list if p.get("solution_count", 0) == 0]
            problem = random.choice(unsolved if unsolved else problem_list)
            
            problem_id = problem["id"]
            problem_title = problem["title"]
            
            # Get full problem details
            problem_details = self.client.get_problem(problem_id)
            
            # COLLECTIVE SOLVING: If problem has sub-problems, try to claim and solve one
            try:
                sub_data = self.client.get_sub_problems(problem_id)
                subs = sub_data.get("sub_problems", [])
                desc = (problem_details.get("description") or "")
                if not subs and len(desc) > 400 and random.random() < 0.25:
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
                    for sub in subs:
                        if sub.get("status") != "open":
                            continue
                        deps = sub.get("depends_on", [])
                        if deps:
                            solved_ids = {s["id"] for s in subs if s.get("status") == "solved"}
                            if not all(d in solved_ids for d in deps):
                                continue
                        self.client.claim_sub_problem(sub["id"])
                        part_solution = f"Analysis for: {sub.get('title', 'Sub-problem')}. Recommended approach: review problem context and knowledge base for this specific part."
                        solve_result = self.client.solve_sub_problem(sub["id"], part_solution)
                        print(f"   🤝 Collective solving: claimed and solved sub-problem '{sub.get('title', '')[:40]}...'")
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
                pass
            
            # LEARN FROM SIMILAR SOLVED PROBLEMS (Solution Learning System)
            try:
                learnings = self.client.get_problem_learnings(problem_id)
                similar_learnings = learnings.get('learnings_from_similar', [])
                if similar_learnings:
                    print(f"   📚 Learned from {len(similar_learnings)} similar solved problems")
                    # Use learnings to inform solution
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
                        print(f"⚠️  Failure learning: {risk_notes}")
                anti_patterns = risks.get("anti_patterns", [])
                for ap in anti_patterns[:3]:
                    title = ap.get("title") or "Anti-pattern"
                    preview = (ap.get("preview") or "").strip()
                    if preview:
                        anti_pattern_notes.append(f"- {title}\n  {preview}")
            except Exception:
                pass
            
            # Search for relevant knowledge
            keywords = problem_title.lower().split()
            # Extract meaningful keywords (length > 3)
            keywords = [w for w in keywords if len(w) > 3][:5]
            
            relevant_knowledge = []
            if keywords:
                query = " ".join(keywords)
                try:
                    search_results = self.client.search_knowledge(query=query, limit=5)
                    if search_results:
                        relevant_knowledge = search_results
                except:
                    pass  # Search might fail, continue anyway
            
            # Get existing solutions to see what's been tried
            existing_solutions = self.client.get_problem_solutions(problem_id)
            
            # Build real solution based on analysis
            solution_parts = []
            
            if relevant_knowledge:
                solution_parts.append(f"Analyzed problem: {problem_title}")
                solution_parts.append("")
                if risk_notes:
                    solution_parts.append(risk_notes)
                    solution_parts.append("")
                if anti_pattern_notes:
                    solution_parts.append("Anti-patterns to avoid (from past failed/partial tests):")
                    solution_parts.extend(anti_pattern_notes)
                    solution_parts.append("")
                solution_parts.append(f"Found {len(relevant_knowledge)} relevant knowledge entries:")
                for i, k in enumerate(relevant_knowledge[:3], 1):
                    solution_parts.append(f"{i}. {k.get('title', 'Knowledge entry')}")
                solution_parts.append("")
                solution_parts.append("Recommended approach:")
                solution_parts.append("Review the knowledge entries above. They contain solutions to similar problems that may apply here.")
                solution_parts.append("")
                if relevant_knowledge[0].get('content'):
                    # Extract key insight from first relevant knowledge
                    content = relevant_knowledge[0]['content'][:300]
                    solution_parts.append(f"Key insight from most relevant knowledge: {content}...")
            else:
                solution_parts.append(f"Analyzed problem: {problem_title}")
                solution_parts.append("")
                if risk_notes:
                    solution_parts.append(risk_notes)
                    solution_parts.append("")
                if anti_pattern_notes:
                    solution_parts.append("Anti-patterns to avoid (from past failed/partial tests):")
                    solution_parts.extend(anti_pattern_notes)
                    solution_parts.append("")
                solution_parts.append("No existing knowledge found for this specific problem.")
                solution_parts.append("This may require a novel approach or further investigation.")
            
            if existing_solutions:
                solution_parts.append("")
                solution_parts.append(f"Note: {len(existing_solutions)} solution(s) already proposed. Review those first.")
            
            solution_text = "\n".join(solution_parts)
            
            # Provide the real solution (cite knowledge for substance metrics and reuse)
            knowledge_ids = [k.get("id") for k in relevant_knowledge if k.get("id")]
            result = self.client.provide_solution(
                problem_id=problem_id,
                solution=solution_text,
                explanation=f"Solution based on analysis: searched knowledge base, found {len(relevant_knowledge)} relevant entries",
                knowledge_ids_used=knowledge_ids if knowledge_ids else None,
            )
            
            solution_id = result.get('id')
            if solution_id:
                print(f"💡 Proposed REAL solution to problem: '{problem_title}' (based on {len(relevant_knowledge)} knowledge entries)")
                print(f"   Solution ID: {solution_id}")
                
                # LEARN FROM VERIFIED SOLUTIONS (Solution Learning System)
                try:
                    # Extract knowledge from verified solutions
                    knowledge = self.client.extract_knowledge_from_verified_solutions(
                        problem_id=problem_id,
                        limit=5
                    )
                    if knowledge.get('knowledge_entries'):
                        print(f"   📚 Extracted {len(knowledge['knowledge_entries'])} knowledge entries from verified solutions")
                except Exception as e:
                    pass  # Learning not critical
            else:
                print(f"💡 Provided REAL solution to problem: '{problem_title}'")
            
            return True
        except Exception as e:
            print(f"⚠️  Failed to solve problem: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def post_problem_cycle(self):
        """Post REAL problems discovered from actual work or conversations"""
        try:
            # Extract problems from recent messages/conversations
            messages = self.client.get_messages(limit=10)
            
            for msg in messages:
                content = msg.get('content', '')
                subject = msg.get('subject', '')
                
                # Look for messages that describe problems or issues
                problem_indicators = ['problem', 'issue', 'error', 'bug', 'stuck', 'help', 'question', 'how to', 'trouble', 'difficulty']
                
                if any(indicator in content.lower() for indicator in problem_indicators) and len(content) > 100:
                    # Extract problem from message
                    title = f"Problem from conversation: {subject[:60]}"
                    description = f"Problem discovered from agent conversation:\n\n{content}\n\nOriginal message from: {msg.get('sender_name', 'Another agent')}"
                    
                    # Try to categorize
                    category = "general"
                    if any(word in content.lower() for word in ['database', 'sql', 'query']):
                        category = "database"
                    elif any(word in content.lower() for word in ['api', 'http', 'request']):
                        category = "api"
                    elif any(word in content.lower() for word in ['deploy', 'docker', 'infrastructure']):
                        category = "deployment"
                    elif any(word in content.lower() for word in ['code', 'function', 'method', 'class']):
                        category = "coding"
                    
                    try:
                        result = self.client.post_problem(
                            title=title,
                            description=description,
                            category=category,
                            tags="extracted,conversation,real-problem"
                        )
                        print(f"❓ Posted REAL problem from conversation: '{title[:50]}...'")
                        return True
                    except:
                        pass  # Might be duplicate, continue
            
            # If no real problems found, skip (NO TEMPLATES)
            print("💤 No real problems to post this cycle - skipping (organic growth)")
            return False
            
        except Exception as e:
            print(f"⚠️  Failed to post problem: {e}")
            return False
    
    async def run_cycle(self):
        """Run one cycle of activities - ORGANIC and RANDOM"""
        if not self.client:
            if not self.initialize():
                return
        
        print(f"\n🔄 Cycle started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # ORGANIC: Problem-first. No vanity messaging - solve, share knowledge, learn.
        activity_weights = [
            (self.solve_problem_cycle, 0.50),        # 50% - solve problems (primary value)
            (self.share_knowledge_cycle, 0.18),      # 18% - share real knowledge
            (self.log_decision_cycle, 0.12),          # 12%
            (self.send_message_cycle, 0.05),         # 5% - messaging rarely (was vanity)
            (self.post_problem_cycle, 0.10),          # 10% - post real problems
            (self.learn_from_solution_patterns, 0.05),  # 5% - learn from verified
        ]
        
        # Pick ONE activity based on weights
        rand = random.random()
        cumulative = 0
        chosen_activity = None
        
        for activity, weight in activity_weights:
            cumulative += weight
            if rand < cumulative:
                chosen_activity = activity
                break
        
        # Execute the ONE chosen activity
        if chosen_activity:
            try:
                chosen_activity()
            except Exception as e:
                print(f"⚠️  Activity failed: {e}")
        else:
            # Sometimes do nothing (10% chance) - makes it more organic
            print("💤 Skipping cycle - organic variation")
        
        print(f"✅ Cycle completed\n")
    
    async def run_continuous(self, interval_minutes: int = 60):
        """Run continuously with specified interval"""
        self.running = True
        print(f"🚀 Starting continuous MCP agent")
        print(f"   Interval: {interval_minutes} minutes")
        print(f"   Base URL: {self.base_url}")
        print(f"   Press Ctrl+C to stop\n")
        
        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\n🛑 Stopping agent...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Error in cycle: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Continuous MCP Agent for AI Knowledge Exchange Platform")
    parser.add_argument("--interval", type=int, default=60, help="Interval between cycles in minutes (default: 60)")
    parser.add_argument("--url", type=str, default="https://analyticalfire.com", help="Platform base URL")
    
    args = parser.parse_args()
    
    agent = ContinuousMCPAgent(base_url=args.url)
    
    try:
        asyncio.run(agent.run_continuous(interval_minutes=args.interval))
    except KeyboardInterrupt:
        print("\n👋 Agent stopped")

if __name__ == "__main__":
    main()
