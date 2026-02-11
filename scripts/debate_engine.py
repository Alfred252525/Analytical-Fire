#!/usr/bin/env python3
"""
Debate Engine - Multi-perspective problem solving through structured AI debate.

Takes a real problem. Sends it to multiple AI "perspectives" (different system prompts
emphasizing different concerns). Each perspective proposes a solution, then critiques
the others. Converges on a consensus with documented trade-offs and dissent.

The output is REAL knowledge: a multi-perspective, debated solution to a real problem.

Requires: ANTHROPIC_API_KEY or OPENAI_API_KEY in environment.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Handle SSL cert issues (macOS Python)
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()


# ── Perspectives ────────────────────────────────────────────────────
# Each perspective is a different expert who will analyze the same problem.
# They WILL disagree. That's the point.

PERSPECTIVES = {
    "pragmatist": {
        "name": "The Pragmatist",
        "model": "anthropic",  # Claude: concise, structured, practical
        "system": (
            "You are a pragmatic senior software engineer. You value simplicity, "
            "readability, and getting things done. You prefer the simplest solution "
            "that works correctly. You push back on over-engineering. You ask: "
            "'What's the simplest thing that could possibly work?' You cite specific "
            "code patterns and concrete steps. Keep your response focused and under 400 words."
        ),
    },
    "security": {
        "name": "The Security Engineer",
        "model": "openai",  # GPT-4: different training data, different blind spots
        "system": (
            "You are a security-focused engineer. You immediately spot injection risks, "
            "auth bypasses, data leaks, race conditions, and supply chain issues. "
            "You review every solution for security implications. You suggest hardening "
            "steps others miss. You ask: 'What could an attacker do with this?' "
            "Be specific about risks and mitigations. Keep your response under 400 words."
        ),
    },
    "architect": {
        "name": "The Architect",
        "model": "anthropic",  # Claude: strong at system design reasoning
        "system": (
            "You are a systems architect who thinks about scalability, maintainability, "
            "and long-term consequences. You consider: Will this scale? What happens "
            "when requirements change? Is this testable? You think about interfaces, "
            "separation of concerns, and technical debt. Be specific about trade-offs. "
            "Keep your response under 400 words."
        ),
    },
    "performance": {
        "name": "The Performance Engineer",
        "model": "openai",  # GPT-4: strong at quantitative reasoning
        "system": (
            "You are a performance engineer. You think about time complexity, memory "
            "usage, latency, throughput, and resource costs. You spot N+1 queries, "
            "unnecessary allocations, blocking I/O, and cache misses. You quantify: "
            "'This will be O(n^2) because...' or 'This blocks the event loop for...'. "
            "Be specific with numbers and benchmarks. Keep your response under 400 words."
        ),
    },
    # ── Finance / Economics perspectives ──
    "market_analyst": {
        "name": "The Market Analyst",
        "model": "openai",
        "system": (
            "You are a quantitative market analyst. You think in terms of data, "
            "historical patterns, risk-adjusted returns, and market mechanics. "
            "You cite real market examples and quantify trade-offs. You distrust "
            "narratives without data. You ask: 'What does the data actually show?' "
            "Keep your response under 400 words."
        ),
    },
    "economist": {
        "name": "The Economist",
        "model": "anthropic",
        "system": (
            "You are a macroeconomist. You think about incentive structures, "
            "second-order effects, unintended consequences, and systemic risks. "
            "You consider both Keynesian and Austrian perspectives. You ask: "
            "'What are the incentives, and what happens at scale?' "
            "Keep your response under 400 words."
        ),
    },
    "risk_analyst": {
        "name": "The Risk Analyst",
        "model": "openai",
        "system": (
            "You are a risk analyst. You think about tail risks, black swans, "
            "correlation in stress scenarios, and what can go wrong. You always "
            "ask: 'What's the worst case, and how likely is it?' You stress-test "
            "optimistic assumptions. Keep your response under 400 words."
        ),
    },
    # ── Geopolitics / Policy perspectives ──
    "strategist": {
        "name": "The Strategist",
        "model": "anthropic",
        "system": (
            "You are a geopolitical strategist. You think about power dynamics, "
            "alliances, deterrence, and long-term national interests. You consider "
            "historical precedents and game theory. You ask: 'Who benefits, and what "
            "are they likely to do next?' Keep your response under 400 words."
        ),
    },
    "policy_analyst": {
        "name": "The Policy Analyst",
        "model": "openai",
        "system": (
            "You are a policy analyst. You think about implementation feasibility, "
            "stakeholder impacts, regulatory frameworks, and political economy. "
            "You ask: 'Can this actually be implemented, and who wins and loses?' "
            "You ground your analysis in real-world policy examples. "
            "Keep your response under 400 words."
        ),
    },
    # ── Philosophy / Ethics perspectives ──
    "philosopher": {
        "name": "The Philosopher",
        "model": "anthropic",
        "system": (
            "You are a philosopher. You examine assumptions, challenge definitions, "
            "and explore implications others overlook. You draw on major philosophical "
            "traditions (analytic, continental, pragmatist, Eastern). You ask: "
            "'What do we actually mean by that, and does the argument hold?' "
            "Keep your response under 400 words."
        ),
    },
    "ethicist": {
        "name": "The Ethicist",
        "model": "openai",
        "system": (
            "You are an applied ethicist. You consider utilitarian, deontological, "
            "virtue ethics, and care ethics perspectives. You think about who is "
            "affected, what rights are at stake, and what precedent is set. "
            "You ask: 'Is this right, and for whom?' Keep your response under 400 words."
        ),
    },
    # ── Business / Strategy perspectives ──
    "business_strategist": {
        "name": "The Business Strategist",
        "model": "anthropic",
        "system": (
            "You are a business strategist. You think about competitive advantage, "
            "market positioning, unit economics, and sustainable growth. You cite "
            "real company examples. You ask: 'What's the moat, and does the math work?' "
            "Keep your response under 400 words."
        ),
    },
    "operator": {
        "name": "The Operator",
        "model": "openai",
        "system": (
            "You are a hands-on operator who has built and run businesses. You think "
            "about execution, team, cash flow, and what actually works vs. what sounds "
            "good in theory. You push back on strategy that ignores operational reality. "
            "You ask: 'Have you actually tried this? What happened?' "
            "Keep your response under 400 words."
        ),
    },
}

# Domain-specific panels
DOMAIN_PANELS = {
    # Tech panels
    "devops": ["pragmatist", "security", "architect"],
    "security": ["security", "architect", "pragmatist"],
    "database": ["pragmatist", "performance", "architect"],
    "api": ["pragmatist", "security", "architect"],
    "frontend": ["pragmatist", "architect", "performance"],
    "testing": ["pragmatist", "architect", "security"],
    "performance": ["performance", "architect", "pragmatist"],
    "python": ["pragmatist", "security", "architect"],
    "javascript": ["pragmatist", "security", "architect"],
    "golang": ["pragmatist", "performance", "architect"],
    "rust": ["pragmatist", "performance", "security"],
    # Finance / Economics panels
    "finance": ["market_analyst", "economist", "risk_analyst"],
    "economics": ["economist", "market_analyst", "policy_analyst"],
    # Geopolitics / Policy panels
    "geopolitics": ["strategist", "policy_analyst", "economist"],
    # Philosophy / Ethics panels
    "philosophy": ["philosopher", "ethicist", "strategist"],
    # Business panels
    "business": ["business_strategist", "operator", "economist"],
    # General: mix of tech and non-tech
    "general": ["pragmatist", "architect", "economist"],
}

# Default fallback panel
DEFAULT_PANEL = ["pragmatist", "security", "architect"]


def get_panel_for_domain(category: str) -> List[str]:
    """Select the right expert panel based on problem domain."""
    return DOMAIN_PANELS.get(category, DEFAULT_PANEL)


# ── LLM Providers ──────────────────────────────────────────────────


def _call_anthropic(
    system: str, user_message: str, model: str = "claude-sonnet-4-20250514"
) -> Optional[str]:
    """Call Anthropic Claude API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    payload = json.dumps({
        "model": model,
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    }).encode("utf-8")

    req = Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=60, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            blocks = data.get("content", [])
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except Exception as exc:
        print(f"  [anthropic] Error: {exc}")
        return None


def _call_openai(
    system: str, user_message: str, model: str = "gpt-4o-mini"
) -> Optional[str]:
    """Call OpenAI API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    payload = json.dumps({
        "model": model,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    }).encode("utf-8")

    req = Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=60, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            return choices[0]["message"]["content"] if choices else None
    except Exception as exc:
        print(f"  [openai] Error: {exc}")
        return None


def call_llm(system: str, user_message: str, prefer: str = "anthropic") -> Optional[str]:
    """
    Call an LLM provider.

    Args:
        prefer: "anthropic" or "openai" — which provider to try first.
                For cross-model debate, each perspective specifies its preferred model.
                Falls back to the other provider if the preferred one is unavailable.
    """
    if prefer == "openai":
        result = _call_openai(system, user_message)
        if result:
            return result
        result = _call_anthropic(system, user_message)
        if result:
            return result
    else:
        result = _call_anthropic(system, user_message)
        if result:
            return result
        result = _call_openai(system, user_message)
        if result:
            return result
    print("  [llm] No LLM provider available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")
    return None


# ── Debate Protocol ─────────────────────────────────────────────────


def run_debate(
    problem: Dict[str, Any],
    panel: Optional[List[str]] = None,
    rounds: int = 2,
    prior_knowledge: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Run a structured multi-perspective debate on a problem.

    Round 0 (if prior_knowledge): Feed relevant prior knowledge to debaters.
    Round 1: Each perspective proposes their solution independently.
    Round 2: Each perspective critiques the others and refines.
    Final: Synthesize consensus + documented disagreements.

    Returns a debate result dict with all contributions and the consensus.
    """
    panel_ids = panel or DEFAULT_PANEL
    perspectives = {pid: PERSPECTIVES[pid] for pid in panel_ids if pid in PERSPECTIVES}

    if not perspectives:
        print("  [debate] No valid perspectives selected.")
        return None

    title = problem.get("title", "Unknown problem")
    description = problem.get("description", "")[:2000]
    source = problem.get("source", "unknown")
    url = problem.get("url", "")

    problem_text = f"**Problem:** {title}\n\n{description}"
    if url:
        problem_text += f"\n\n**Source:** {url}"

    # ── Build prior knowledge context ──
    prior_context = ""
    if prior_knowledge:
        prior_parts = []
        for i, entry in enumerate(prior_knowledge[:3], 1):
            pk_title = entry.get("title", "Unknown")[:80]
            pk_content = entry.get("content", "")[:600]
            prior_parts.append(f"**Prior Knowledge {i}: {pk_title}**\n{pk_content}")
        prior_context = (
            "\n\n---\n**Relevant prior knowledge from our platform "
            "(previous debates and solutions):**\n\n"
            + "\n\n".join(prior_parts)
            + "\n\nConsider this prior knowledge when proposing your solution. "
            "Build on it, challenge it, or reference it where relevant.\n---\n"
        )
        print(f"  [knowledge] Feeding {len(prior_knowledge)} prior entries to debaters")

    print(f"\n{'='*60}")
    print(f"DEBATE: {title[:60]}")
    print(f"{'='*60}")

    # ── Round 1: Independent proposals ──
    print(f"\n--- Round 1: Independent Proposals ---")
    proposals: Dict[str, str] = {}
    for pid, perspective in perspectives.items():
        model_pref = perspective.get("model", "anthropic")
        model_label = "Claude" if model_pref == "anthropic" else "GPT-4"
        print(f"  [{perspective['name']}] ({model_label}) Proposing solution...")
        prompt = (
            f"A real developer is asking for help with this problem:\n\n"
            f"{problem_text}\n\n"
            f"{prior_context}"
            f"Propose your solution. Be specific: include code snippets, concrete steps, "
            f"and explain WHY your approach is the right one. Address potential issues."
        )
        response = call_llm(perspective["system"], prompt, prefer=model_pref)
        if response:
            proposals[pid] = response
            print(f"  [{perspective['name']}] Done ({len(response)} chars)")
        else:
            print(f"  [{perspective['name']}] Failed to respond")
        time.sleep(0.5)  # rate limit

    if len(proposals) < 2:
        print("  [debate] Not enough perspectives responded.")
        return None

    # ── Round 2: Critique and refine ──
    print(f"\n--- Round 2: Critique & Refinement ---")
    critiques: Dict[str, str] = {}
    for pid, perspective in perspectives.items():
        if pid not in proposals:
            continue

        # Show this perspective what the others proposed
        others_text = ""
        for other_pid, other_proposal in proposals.items():
            if other_pid == pid:
                continue
            other_name = perspectives[other_pid]["name"]
            others_text += f"\n**{other_name}'s proposal:**\n{other_proposal}\n"

        model_pref = perspective.get("model", "anthropic")
        model_label = "Claude" if model_pref == "anthropic" else "GPT-4"
        print(f"  [{perspective['name']}] ({model_label}) Reviewing other proposals...")
        prompt = (
            f"You previously proposed a solution to this problem:\n\n"
            f"{problem_text}\n\n"
            f"**Your proposal:**\n{proposals[pid]}\n\n"
            f"Now review the other experts' proposals:{others_text}\n\n"
            f"Critique the other proposals. What do they get right? What do they miss? "
            f"Where do you agree and disagree? Refine your recommendation considering "
            f"their points. Be specific about trade-offs."
        )
        response = call_llm(perspective["system"], prompt, prefer=model_pref)
        if response:
            critiques[pid] = response
            print(f"  [{perspective['name']}] Done ({len(response)} chars)")
        else:
            print(f"  [{perspective['name']}] Failed to respond")
        time.sleep(0.5)

    # ── Consensus synthesis ──
    print(f"\n--- Synthesizing Consensus ---")
    all_contributions = ""
    for pid in perspectives:
        name = perspectives[pid]["name"]
        if pid in proposals:
            all_contributions += f"\n## {name} - Initial Proposal\n{proposals[pid]}\n"
        if pid in critiques:
            all_contributions += f"\n## {name} - After Debate\n{critiques[pid]}\n"

    consensus_prompt = (
        f"You are synthesizing a multi-expert debate about this problem:\n\n"
        f"{problem_text}\n\n"
        f"Here are all the expert contributions:\n{all_contributions}\n\n"
        f"Write a consensus summary:\n"
        f"1. **Agreed Solution** - What all experts converge on (specific steps/code)\n"
        f"2. **Key Trade-offs** - Where experts disagreed and why both sides have a point\n"
        f"3. **Recommended Approach** - Your synthesized recommendation\n"
        f"4. **Pitfalls to Avoid** - Things at least one expert flagged as dangerous\n\n"
        f"Be concrete. Include code if the experts provided it. This should be directly "
        f"actionable by a developer facing this problem."
    )
    consensus_system = (
        "You are a senior tech lead synthesizing a multi-expert debate into an actionable "
        "recommendation. Be fair to all perspectives. Highlight real trade-offs, don't "
        "paper over disagreements. The output should be directly useful to someone with "
        "this problem."
    )
    consensus = call_llm(consensus_system, consensus_prompt)
    if not consensus:
        print("  [debate] Failed to synthesize consensus.")
        # Fall back to just the proposals
        consensus = "Consensus synthesis failed. See individual proposals below.\n\n" + all_contributions

    print(f"  Consensus synthesized ({len(consensus)} chars)")

    return {
        "problem": problem,
        "panel": list(perspectives.keys()),
        "panel_names": {pid: p["name"] for pid, p in perspectives.items()},
        "panel_models": {pid: ("Claude" if p.get("model") == "anthropic" else "GPT-4") for pid, p in perspectives.items()},
        "proposals": proposals,
        "critiques": critiques,
        "consensus": consensus,
        "debated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def debate_to_knowledge(debate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a debate result into a knowledge entry for the platform.
    The debate itself IS the knowledge.
    """
    problem = debate.get("problem", {})
    title = problem.get("title", "Unknown")[:80]
    source = problem.get("source", "unknown")
    url = problem.get("url", "")
    category = problem.get("category", "general")
    tags = problem.get("tags", [])

    panel_names = debate.get("panel_names", {})
    panel_models = debate.get("panel_models", {})
    panel_str = ", ".join(
        f"{name} ({panel_models.get(pid, '?')})" for pid, name in panel_names.items()
    )

    # Build the knowledge content
    content_parts = [
        f"# Multi-Perspective Solution: {title}",
        f"",
        f"**Source:** {source} ({url})" if url else f"**Source:** {source}",
        f"**Debated by:** {panel_str}",
        f"**Date:** {debate.get('debated_at', 'unknown')}",
        f"",
        f"---",
        f"",
        f"## Consensus",
        f"",
        debate.get("consensus", "No consensus reached."),
        f"",
        f"---",
        f"",
        f"## Individual Expert Proposals",
        f"",
    ]

    for pid, proposal in debate.get("proposals", {}).items():
        name = panel_names.get(pid, pid)
        model = panel_models.get(pid, "")
        content_parts.append(f"### {name} ({model})")
        content_parts.append(f"")
        content_parts.append(proposal)
        content_parts.append(f"")

        critique = debate.get("critiques", {}).get(pid)
        if critique:
            content_parts.append(f"**After reviewing other proposals:**")
            content_parts.append(f"")
            content_parts.append(critique)
            content_parts.append(f"")

    content = "\n".join(content_parts)

    # Add debate-specific tags
    debate_tags = list(set(tags + ["multi-perspective", "debated", "consensus"]))[:10]

    return {
        "title": f"Debated Solution: {title}",
        "content": content[:10000],  # Platform limit
        "category": category,
        "tags": debate_tags,
    }


# ── CLI ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a multi-perspective AI debate on a problem")
    parser.add_argument("--title", required=True, help="Problem title")
    parser.add_argument("--description", required=True, help="Problem description")
    parser.add_argument("--source", default="manual", help="Problem source")
    parser.add_argument("--url", default="", help="Problem URL")
    parser.add_argument("--panel", nargs="+", default=DEFAULT_PANEL, help="Perspective IDs")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    problem = {
        "title": args.title,
        "description": args.description,
        "source": args.source,
        "url": args.url,
        "category": "general",
        "tags": [],
    }

    result = run_debate(problem, panel=args.panel)
    if result:
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            knowledge = debate_to_knowledge(result)
            print(f"\n{'='*60}")
            print(f"KNOWLEDGE OUTPUT")
            print(f"{'='*60}")
            print(f"Title: {knowledge['title']}")
            print(f"Category: {knowledge['category']}")
            print(f"Tags: {knowledge['tags']}")
            print(f"\n{knowledge['content'][:2000]}...")
    else:
        print("Debate failed. Check LLM API key.")
        sys.exit(1)
