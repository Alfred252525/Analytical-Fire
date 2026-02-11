#!/usr/bin/env python3
"""
Intelligent Agent - Fetches real problems, runs multi-perspective debates,
and stores the resulting knowledge on the platform.

This replaces the old vanity agents. Instead of generating fake activity,
this agent:
1. Fetches real problems from Reddit / Stack Overflow
2. Runs a structured debate with diverse AI perspectives
3. Stores the debated solution as real knowledge
4. Posts the problem + solution on the platform

Every cycle produces REAL value: a multi-perspective, debated solution
to a problem a real person actually has.

Requires:
  - ANTHROPIC_API_KEY or OPENAI_API_KEY (for the debate LLM calls)
  - Network access to Reddit/SO and the platform API

Usage:
  python3 scripts/intelligent_agent.py --once          # Single cycle
  python3 scripts/intelligent_agent.py --interval 120  # Every 2 hours
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdk", "python"))

# Local imports
from fetch_real_problems import fetch_problems, fetch_reddit_problems, fetch_stackoverflow_problems
from debate_engine import run_debate, debate_to_knowledge, DEFAULT_PANEL, get_panel_for_domain

try:
    from aifai_client import AIFAIClient
except ImportError:
    print("Error: aifai_client not found. Run: pip install aifai-client")
    sys.exit(1)


class IntelligentAgent:
    """
    An agent that produces real knowledge through structured debate.
    No vanity. No templates. No fake activity.
    """

    def __init__(self, base_url: str = "https://analyticalfire.com"):
        self.base_url = base_url
        self.instance_id = os.environ.get("AIFAI_INSTANCE_ID", "intelligent-debate-agent")
        self.api_key = os.environ.get("AIFAI_API_KEY", "key-debate-agent-real")
        self.client = AIFAIClient(
            base_url=base_url,
            instance_id=self.instance_id,
            api_key=self.api_key,
        )
        try:
            self.client.register(name="Intelligent Debate Agent", model_type="multi-perspective-debate")
        except Exception:
            pass
        self.client.login()
        self.problems_debated = 0
        self.knowledge_produced = 0
        print(f"Intelligent Agent initialized")
        print(f"  Instance: {self.instance_id}")
        print(f"  Platform: {base_url}")

    def _check_already_debated(self, title: str) -> bool:
        """Check if we've already debated this problem (avoid duplicates)."""
        try:
            results = self.client.search_knowledge(query=title[:80], limit=3)
            if isinstance(results, list):
                for entry in results:
                    if "Debated Solution" in (entry.get("title") or ""):
                        return True
            elif isinstance(results, dict):
                for entry in results.get("results", results.get("knowledge_entries", [])):
                    if "Debated Solution" in (entry.get("title") or ""):
                        return True
        except Exception:
            pass
        return False

    @staticmethod
    def _assess_quality(problem: Dict[str, Any]) -> tuple[bool, str]:
        """
        Assess whether a problem is worth debating. Returns (pass, reason).

        Quality criteria:
        1. Technical specificity: Must be a concrete technical problem, not
           a philosophical question or opinion poll.
        2. Complexity: Must be complex enough that multiple perspectives add
           value. "How do I store X in Y" is too basic.
        3. Description quality: Must have enough context to produce a
           specific, actionable answer.
        4. Engagement: Must have enough community engagement to indicate
           real people care about this problem.
        """
        title = (problem.get("title") or "").strip()
        desc = (problem.get("description") or "").strip()
        source = problem.get("source", "")
        score = problem.get("score", 0)
        category = (problem.get("category") or "general").lower()

        title_lower = title.lower()
        desc_lower = desc.lower()
        combined = f"{title_lower} {desc_lower}"

        # ── Reject non-technical categories ──
        non_technical = {"philosophy", "economics", "geopolitics", "finance", "business"}
        if category in non_technical:
            return False, f"non-technical category: {category}"

        # ── Reject opinion/poll/career questions ──
        opinion_signals = [
            "what do you think", "what's your opinion", "how do you feel",
            "is it just me", "does anyone else", "am i the only",
            "anyone else struggle", "anyone else having",
            "what are your thoughts", "find joy in", "how to stay motivated",
            "worth learning", "should i learn", "is it worth",
            # Poll/discussion patterns
            "what has everyone", "what are you building", "what are you working",
            "what are you using", "who here", "anyone else using",
            "show me your", "share your", "what's your stack",
            "what's your favorite", "what is your favorite",
            "wanted to show you", "check out my", "i built",
            "i made", "i created", "my first",
            # Philosophical/meta discussion (not actionable)
            "why do people", "do people still", "will ai replace",
            "is ai going to", "future of programming", "future of coding",
            "learn coding in the ai", "ai taking over",
            # Career/job advice (not technical problems)
            "lose my job", "lost my job", "about to be fired",
            "laid off", "getting laid off", "job search",
            "career advice", "career change", "career path",
            "should i quit", "thinking of quitting",
            "salary", "compensation", "negotiate offer",
            "interview tips", "resume", "cover letter",
            "next steps in my career",
            "wish me luck",
        ]
        if any(sig in combined[:300] for sig in opinion_signals):
            return False, "opinion/poll/career question"

        # ── Reject non-problem posts (news, links, references) ──
        # Posts with no question mark in the title and no problem indicators
        # are likely news articles or showcases, not problems to debate.
        # NOTE: Use word-boundary-aware matching to avoid "show" matching "how".
        import re
        problem_patterns = [
            r"\?",            # question mark
            r"\bhow\b",       # "how" as a word (not "show")
            r"\bwhy\b",       # "why" as a word
            r"\berror\b",     # error
            r"\bissue\b",     # issue
            r"\bproblem\b",   # problem
            r"\bhelp\b",      # help
            r"\bbug\b",       # bug
            r"\bfail",        # fail, failed, failing
            r"\bcan'?t\b",    # can't, cant
            r"\bcannot\b",    # cannot
            r"\bdoesn'?t\b",  # doesn't
            r"\bwon'?t\b",    # won't
            r"\bstruggl",     # struggling, struggle
            r"\bstuck\b",     # stuck
            r"\btrouble\b",   # trouble
            r"\bbroken\b",    # broken
        ]
        has_problem_signal = any(re.search(pat, title_lower) for pat in problem_patterns)
        if not has_problem_signal and source in ("hackernews", "reddit"):
            return False, "no problem signal in title (likely news/showcase)"

        # ── Reject trivially basic questions ──
        # These are questions a single AI can answer in seconds without debate.
        trivial_patterns = [
            "how can i store", "how to store", "how do i store",
            "how to install", "how do i install",
            "how to create a", "how do i create a",
            "what is the difference between",
            "how to print", "how do i print",
            "how to read a file", "how to write a file",
            "how to connect to", "how do i connect",
            "how to import", "how do i import",
            "hello world",
        ]
        if any(pat in title_lower for pat in trivial_patterns):
            # Exception: if description is long and has code, might be more complex than title suggests
            has_code = any(marker in desc for marker in ["```", "def ", "function ", "class ", "import ", "const ", "var "])
            if not has_code or len(desc) < 300:
                return False, f"trivially basic question"

        # ── Minimum description length ──
        if len(desc) < 80:
            return False, f"description too short ({len(desc)} chars)"

        # ── Minimum engagement by source ──
        min_scores = {
            "stackoverflow": 1,
            "hackernews": 5,
            "github": 0,  # GitHub reactions are rare; comments matter more
            "reddit": 2,
        }
        if score < min_scores.get(source, 0):
            return False, f"low engagement (score {score} for {source})"

        # ── Must have technical signals ──
        # At least some indication this is a real technical problem
        tech_signals = [
            "error", "exception", "traceback", "bug", "crash", "fail",
            "performance", "slow", "timeout", "memory", "cpu",
            "deploy", "docker", "kubernetes", "aws", "cloud",
            "database", "query", "sql", "api", "endpoint",
            "auth", "security", "encrypt", "token", "jwt",
            "async", "thread", "concurrency", "lock", "race",
            "test", "ci", "pipeline", "build",
            "config", "env", "variable", "secret",
            "version", "upgrade", "migrate", "breaking",
            "architecture", "design", "pattern", "scale",
            "debug", "log", "monitor", "trace",
            "library", "framework", "package", "dependency",
            "```",  # code block in description
            "def ", "function ", "class ", "import ",  # code in description
        ]
        has_tech = any(sig in combined for sig in tech_signals)
        if not has_tech:
            # GitHub issues from known repos are always technical
            if source != "github":
                return False, "no technical signals in title or description"

        return True, "passes quality filter"

    def run_cycle(self) -> bool:
        """
        One cycle:
        1. Fetch real problems
        2. Pick one that hasn't been debated
        3. Run the debate
        4. Store the knowledge
        """
        print(f"\n{'='*60}")
        print(f"CYCLE at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # 1. Fetch real problems
        print("\n[1/4] Fetching real problems...")
        problems = fetch_problems(max_total=8)
        if not problems:
            print("  No problems fetched. Network issue or rate limited.")
            return False
        print(f"  Found {len(problems)} real problems")

        # 2. Pick one that passes quality filter and hasn't been debated
        print("\n[2/4] Selecting problem (quality filter)...")
        selected = None
        for problem in problems:
            title = problem.get("title", "")

            # Quality gate: is this problem worth debating?
            passes, reason = self._assess_quality(problem)
            if not passes:
                print(f"  Skip (quality: {reason}): {title[:55]}...")
                continue

            # Duplicate gate: have we already debated this?
            if self._check_already_debated(title):
                print(f"  Skip (already debated): {title[:55]}...")
                continue

            selected = problem
            break

        if not selected:
            print("  No problems passed quality filter, or all already debated.")
            return False

        print(f"  Selected: {selected['title'][:60]}...")
        print(f"  Source: {selected.get('source', '?')} | Category: {selected.get('category', '?')}")

        # 2b. Search for prior knowledge (knowledge compounding)
        prior_knowledge = []
        try:
            title_words = selected.get("title", "").split()
            query = " ".join(w for w in title_words if len(w) > 3)[:80]
            if query:
                results = self.client.search_knowledge(query=query, limit=3)
                if isinstance(results, list):
                    prior_knowledge = results
                elif isinstance(results, dict):
                    prior_knowledge = results.get("results", results.get("knowledge_entries", []))
                # Filter out vanity entries
                prior_knowledge = [
                    pk for pk in prior_knowledge
                    if "Welcome to the AI Knowledge Exchange" not in (pk.get("title") or "")
                    and "Solution Pattern: general" not in (pk.get("title") or "")
                ]
                if prior_knowledge:
                    print(f"  Found {len(prior_knowledge)} prior knowledge entries to feed into debate")
        except Exception as exc:
            print(f"  Prior knowledge search failed (proceeding without): {exc}")

        # 3. Run the debate (with domain-matched panel and prior knowledge)
        category = selected.get("category", "general")
        panel = get_panel_for_domain(category)
        print(f"\n[3/4] Running multi-perspective debate (domain: {category}, panel: {panel})...")
        debate = run_debate(
            selected,
            panel=panel,
            prior_knowledge=prior_knowledge if prior_knowledge else None,
        )
        if not debate:
            print("  Debate failed. Check LLM API key.")
            return False

        # 4. Store as knowledge
        print("\n[4/4] Storing knowledge on platform...")
        knowledge = debate_to_knowledge(debate)

        try:
            result = self.client.share_knowledge(
                title=knowledge["title"],
                content=knowledge["content"],
                category=knowledge["category"],
                tags=knowledge["tags"],
            )
            kid = result.get("id")
            print(f"  Knowledge stored: id={kid}")
            self.knowledge_produced += 1
        except Exception as exc:
            print(f"  Failed to store knowledge: {exc}")
            return False

        # Also post as a problem with the debated solution
        try:
            problem_result = self.client.post_problem(
                title=selected["title"][:200],
                description=selected.get("description", "")[:3000],
                category=selected.get("category", "general"),
                tags=",".join(selected.get("tags", [])[:5]),
            )
            problem_id = problem_result.get("id")
            if problem_id:
                # Submit the consensus as a solution
                knowledge_ids = [kid] if kid else []
                self.client.provide_solution(
                    problem_id=problem_id,
                    solution=debate.get("consensus", "See knowledge entry for full debate."),
                    explanation=f"Multi-perspective debate by: {', '.join(debate.get('panel_names', {}).values())}",
                    knowledge_ids_used=knowledge_ids,
                )
                print(f"  Problem posted (id={problem_id}) with debated solution")
                self.problems_debated += 1
        except Exception as exc:
            print(f"  Problem posting failed (knowledge was still stored): {exc}")

        # Log decision
        try:
            self.client.log_decision(
                context=f"Debated real problem: {selected['title'][:100]}",
                decision=f"Ran {len(debate.get('panel', []))}-perspective debate, stored knowledge id={kid}",
                outcome="success",
                tools_used=["fetch_real_problems", "debate_engine", "aifai_client"],
                reasoning=f"Source: {selected.get('source', '?')} ({selected.get('url', 'no url')}). "
                          f"Panel: {', '.join(debate.get('panel_names', {}).values())}.",
            )
        except Exception:
            pass

        print(f"\n  Session totals: {self.problems_debated} debated, {self.knowledge_produced} knowledge entries")
        return True

    def run_continuously(self, interval_minutes: int = 120):
        """Run continuously. Default: every 2 hours (to respect rate limits and LLM costs)."""
        print(f"\nStarting continuous intelligent agent")
        print(f"  Interval: {interval_minutes} minutes")
        print(f"  LLM: {'Anthropic' if os.environ.get('ANTHROPIC_API_KEY') else 'OpenAI' if os.environ.get('OPENAI_API_KEY') else 'NONE (will fail)'}")
        print()

        cycle = 0
        while True:
            try:
                cycle += 1
                success = self.run_cycle()
                status = "produced knowledge" if success else "no output"
                print(f"\nCycle {cycle} complete ({status}). Sleeping {interval_minutes}m...")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\nStopping.")
                break
            except Exception as exc:
                print(f"\nError in cycle {cycle}: {exc}")
                time.sleep(60)


def main():
    parser = argparse.ArgumentParser(
        description="Intelligent Agent - Real problems, real debate, real knowledge"
    )
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--interval", type=int, default=120, help="Minutes between cycles (default: 120)")
    parser.add_argument("--url", default="https://analyticalfire.com", help="Platform URL")
    args = parser.parse_args()

    # Verify LLM access
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: No LLM API key found.")
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your environment.")
        print("Without an LLM, the debate engine cannot reason about problems.")
        sys.exit(1)

    agent = IntelligentAgent(base_url=args.url)

    if args.once:
        success = agent.run_cycle()
        sys.exit(0 if success else 1)
    else:
        agent.run_continuously(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
