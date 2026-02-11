#!/usr/bin/env python3
"""
Fetch REAL problems from public sources (Stack Overflow, Hacker News, GitHub Issues, Reddit).
These are problems real people are actually stuck on.
No fake problems, no templates, no vanity.
"""

from __future__ import annotations

import json
import random
import re
import ssl
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus

# Handle SSL cert issues (macOS Python)
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE


# Reddit subreddits with real programming problems
# Focused on technical content where multi-perspective debate adds value.
# Non-technical subreddits removed: philosophical/opinion questions don't
# produce actionable knowledge from AI debate.
SUBREDDITS = [
    "Python",
    "node",
    "webdev",
    "devops",
    "golang",
    "rust",
    "typescript",
    "reactjs",
    "django",
    "flask",
    "FastAPI",
    "docker",
    "kubernetes",
    "aws",
    "PostgreSQL",
    "databases",
    "ExperiencedDevs",
    "softwarearchitecture",
    "netsec",
    "sysadmin",
]

# Stack Overflow tags -- focused on areas where failure patterns are most valuable.
# Prioritize infrastructure, async, and integration tags where gotchas are common.
SO_TAGS = [
    "python",
    "fastapi",
    "docker",
    "postgresql",
    "aws",
    "typescript",
    "node.js",
    "kubernetes",
    "redis",
    "sqlalchemy",
    "asyncio",
    "nginx",
    "ssl",
    "cors",
    "websocket",
]

USER_AGENT = "AIFAI-ProblemFetcher/1.0 (AI Knowledge Exchange; research)"


def _get_json(url: str, retries: int = 2) -> Optional[Dict[str, Any]]:
    """Fetch JSON from a URL with retries and polite rate limiting."""
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, json.JSONDecodeError) as exc:
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
            else:
                print(f"  [fetch] Failed {url[:80]}...: {exc}")
                return None
    return None


# ── Reddit ──────────────────────────────────────────────────────────


def fetch_reddit_problems(
    subreddits: Optional[List[str]] = None,
    limit_per_sub: int = 10,
    min_score: int = 1,
    min_comments: int = 0,
    max_problems: int = 10,
) -> List[Dict[str, Any]]:
    """
    Fetch real problems from Reddit.
    Only keeps posts that look like real questions/problems (not memes, showcases, etc.).
    """
    subs = subreddits or random.sample(SUBREDDITS, min(4, len(SUBREDDITS)))
    problems: List[Dict[str, Any]] = []

    for sub in subs:
        url = f"https://www.reddit.com/r/{sub}/new.json?limit={limit_per_sub}"
        data = _get_json(url)
        if not data or "data" not in data:
            time.sleep(1)
            continue

        for child in data["data"].get("children", []):
            post = child.get("data", {})
            title = (post.get("title") or "").strip()
            body = (post.get("selftext") or "").strip()
            score = post.get("score", 0)
            num_comments = post.get("num_comments", 0)

            # Quality filters
            if score < min_score or num_comments < min_comments:
                continue
            if len(title) < 15 or len(body) < 50:
                continue
            # Skip non-question posts (showcases, memes, news)
            if (post.get("link_flair_text") or "").lower() in ("showcase", "meme", "news", "meta"):
                continue
            # Heuristic: looks like a question or problem
            title_lower = title.lower()
            is_question = any(
                kw in title_lower
                for kw in [
                    "how", "why", "error", "issue", "problem", "help",
                    "bug", "fail", "can't", "cannot", "doesn't", "won't",
                    "what", "best way", "struggling", "stuck", "trouble",
                    "advice", "?",
                ]
            )
            if not is_question:
                continue

            problems.append({
                "source": "reddit",
                "subreddit": sub,
                "title": title,
                "description": body[:3000],
                "url": f"https://www.reddit.com{post.get('permalink', '')}",
                "score": score,
                "num_comments": num_comments,
                "created_utc": post.get("created_utc"),
                "category": _categorize_problem(title, body, sub),
                "tags": _extract_tags(title, body, sub),
            })

            if len(problems) >= max_problems:
                break

        time.sleep(1)  # polite rate limit

    return problems[:max_problems]


# ── Stack Overflow ──────────────────────────────────────────────────


def fetch_stackoverflow_problems(
    tags: Optional[List[str]] = None,
    max_problems: int = 10,
    min_score: int = 2,
) -> List[Dict[str, Any]]:
    """
    Fetch real unanswered or active questions from Stack Overflow.
    Uses the public API (no key needed for low-volume).
    """
    chosen_tags = tags or random.sample(SO_TAGS, min(3, len(SO_TAGS)))
    tag_str = ";".join(chosen_tags)
    url = (
        f"https://api.stackexchange.com/2.3/questions"
        f"?order=desc&sort=activity&tagged={quote_plus(tag_str)}"
        f"&site=stackoverflow&filter=withbody&pagesize={max_problems}"
    )
    data = _get_json(url)
    if not data or "items" not in data:
        return []

    problems: List[Dict[str, Any]] = []
    for item in data["items"]:
        title = (item.get("title") or "").strip()
        body_html = (item.get("body") or "").strip()
        # Strip HTML tags for plain text
        body = re.sub(r"<[^>]+>", "", body_html)
        body = re.sub(r"&[a-z]+;", " ", body)
        score = item.get("score", 0)

        if score < min_score or len(body) < 50:
            continue

        so_tags = item.get("tags", [])
        problems.append({
            "source": "stackoverflow",
            "title": title,
            "description": body[:3000],
            "url": item.get("link", ""),
            "score": score,
            "num_answers": item.get("answer_count", 0),
            "is_answered": item.get("is_answered", False),
            "created_utc": item.get("creation_date"),
            "category": _so_category(so_tags),
            "tags": so_tags[:8],
        })

    return problems[:max_problems]


# ── Hacker News ─────────────────────────────────────────────────────

# HN "Ask HN" posts are real questions from real engineers. The API is
# completely open: no auth, no rate-limit issues from cloud IPs.

HN_CATEGORIES = [
    "ask",    # Ask HN posts
]


def fetch_hackernews_problems(
    max_problems: int = 10,
    min_score: int = 10,
) -> List[Dict[str, Any]]:
    """
    Fetch real questions from Hacker News (Ask HN posts and recent questions).
    Uses the official HN Algolia API — open, fast, no auth.
    """
    problems: List[Dict[str, Any]] = []

    # Search for recent Ask HN posts — failure patterns and technical gotchas.
    # Focused on queries that surface problems where multi-perspective debate
    # produces genuinely useful failure knowledge, not general advice.
    for query in [
        "bug", "broke", "regression", "fails silently",
        "production incident", "outage", "postmortem",
        "debugging", "performance issue", "memory leak",
        "migration broke", "upgrade broke", "breaking change",
        "race condition", "deadlock", "timeout",
    ]:
        url = (
            f"https://hn.algolia.com/api/v1/search_by_date"
            f"?tags=ask_hn&query={quote_plus(query)}&hitsPerPage={max_problems}"
        )
        data = _get_json(url)
        if not data or "hits" not in data:
            continue

        for hit in data["hits"]:
            title = (hit.get("title") or "").strip()
            body = (hit.get("story_text") or "").strip()
            # Strip HTML
            body = re.sub(r"<[^>]+>", "", body)
            body = re.sub(r"&[a-z]+;", " ", body)
            score = hit.get("points", 0) or 0
            comments = hit.get("num_comments", 0) or 0

            if score < min_score or len(title) < 20:
                continue
            if len(body) < 100:
                continue

            object_id = hit.get("objectID", "")
            problems.append({
                "source": "hackernews",
                "title": title,
                "description": body[:3000],
                "url": f"https://news.ycombinator.com/item?id={object_id}",
                "score": score,
                "num_comments": comments,
                "created_utc": hit.get("created_at_i"),
                "category": _categorize_problem(title, body, "hackernews"),
                "tags": _extract_tags(title, body, "hackernews"),
            })

            if len(problems) >= max_problems:
                break
        if len(problems) >= max_problems:
            break
        time.sleep(0.3)

    return problems[:max_problems]


# ── GitHub Issues ───────────────────────────────────────────────────

# Popular open-source repos with active issue trackers.
# These are real bugs, real feature requests, real questions.
GITHUB_REPOS = [
    "tiangolo/fastapi",
    "pallets/flask",
    "django/django",
    "encode/httpx",
    "psycopg/psycopg",
    "sqlalchemy/sqlalchemy",
    "docker/compose",
    "hashicorp/terraform",
    "vercel/next.js",
    "denoland/deno",
    "astral-sh/ruff",
    "pydantic/pydantic",
]


def fetch_github_issues(
    repos: Optional[List[str]] = None,
    max_problems: int = 10,
    min_comments: int = 1,
) -> List[Dict[str, Any]]:
    """
    Fetch real open issues from popular GitHub repos.
    Uses the public API (no token needed for low-volume reads).
    """
    chosen_repos = repos or random.sample(GITHUB_REPOS, min(4, len(GITHUB_REPOS)))
    problems: List[Dict[str, Any]] = []

    for repo in chosen_repos:
        url = (
            f"https://api.github.com/repos/{repo}/issues"
            f"?state=open&sort=updated&direction=desc&per_page=5"
        )
        data = _get_json(url)
        if not data or not isinstance(data, list):
            time.sleep(0.5)
            continue

        for issue in data:
            # Skip pull requests (they show up in the issues endpoint)
            if issue.get("pull_request"):
                continue

            title = (issue.get("title") or "").strip()
            body = (issue.get("body") or "").strip()
            # Strip markdown images and long URLs
            body = re.sub(r"!\[.*?\]\(.*?\)", "", body)
            body = re.sub(r"https?://\S{100,}", "[long-url]", body)
            comments = issue.get("comments", 0)

            if comments < min_comments or len(title) < 10:
                continue
            if len(body) < 30:
                continue

            labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]
            gh_tags = [repo.split("/")[1].lower()] + [l.lower() for l in labels[:3]]

            problems.append({
                "source": "github",
                "repo": repo,
                "title": f"[{repo.split('/')[1]}] {title}",
                "description": body[:3000],
                "url": issue.get("html_url", ""),
                "score": issue.get("reactions", {}).get("total_count", 0),
                "num_comments": comments,
                "created_utc": issue.get("created_at"),
                "category": _categorize_problem(title, body, repo),
                "tags": list(set(gh_tags))[:8],
            })

            if len(problems) >= max_problems:
                break

        if len(problems) >= max_problems:
            break
        time.sleep(0.5)

    return problems[:max_problems]


# ── Categorization helpers ──────────────────────────────────────────


def _categorize_problem(title: str, body: str, subreddit: str) -> str:
    text = f"{title} {body} {subreddit}".lower()
    # Tech domains
    if any(w in text for w in ["deploy", "docker", "kubernetes", "aws", "cloud", "terraform"]):
        return "devops"
    if any(w in text for w in ["security", "auth", "jwt", "oauth", "encrypt", "hash"]):
        return "security"
    if any(w in text for w in ["database", "sql", "postgres", "mysql", "mongo", "redis", "query"]):
        return "database"
    if any(w in text for w in ["api", "rest", "endpoint", "fastapi", "express", "route"]):
        return "api"
    if any(w in text for w in ["react", "vue", "angular", "frontend", "css", "html", "ui"]):
        return "frontend"
    if any(w in text for w in ["test", "pytest", "jest", "unittest", "mock"]):
        return "testing"
    if any(w in text for w in ["performance", "optimize", "slow", "memory", "cache"]):
        return "performance"
    if any(w in text for w in ["python", "pip", "import", "module"]):
        return "python"
    if any(w in text for w in ["node", "npm", "javascript", "typescript"]):
        return "javascript"
    if any(w in text for w in ["golang", "go ", "goroutine"]):
        return "golang"
    if any(w in text for w in ["rust", "cargo", "borrow"]):
        return "rust"
    return "general"


def _so_category(tags: List[str]) -> str:
    tag_set = set(t.lower() for t in tags)
    if tag_set & {"docker", "kubernetes", "aws", "devops", "terraform"}:
        return "devops"
    if tag_set & {"security", "authentication", "jwt", "oauth2"}:
        return "security"
    if tag_set & {"postgresql", "mysql", "sql", "mongodb", "database", "redis"}:
        return "database"
    if tag_set & {"fastapi", "django", "flask", "express", "api", "rest"}:
        return "api"
    if tag_set & {"react", "vue", "angular", "css", "html"}:
        return "frontend"
    if tag_set & {"python"}:
        return "python"
    if tag_set & {"javascript", "typescript", "node.js"}:
        return "javascript"
    if tag_set & {"go", "golang"}:
        return "golang"
    if tag_set & {"rust"}:
        return "rust"
    return "general"


def _extract_tags(title: str, body: str, subreddit: str) -> List[str]:
    text = f"{title} {body}".lower()
    tags = [subreddit.lower()]
    keywords = [
        "python", "javascript", "typescript", "golang", "rust", "java",
        "docker", "kubernetes", "aws", "terraform", "fastapi", "django",
        "flask", "react", "vue", "angular", "postgresql", "mysql",
        "mongodb", "redis", "git", "linux", "nginx", "celery",
        "jwt", "oauth", "graphql", "websocket", "grpc",
        "async", "concurrency", "performance", "security",
        "ci-cd", "testing", "monitoring", "logging",
    ]
    for kw in keywords:
        if kw in text and kw not in tags:
            tags.append(kw)
    return tags[:8]


# ── Main ────────────────────────────────────────────────────────────


def fetch_problems(max_total: int = 10) -> List[Dict[str, Any]]:
    """Fetch problems from all sources, deduplicated and shuffled."""
    so = fetch_stackoverflow_problems(max_problems=max_total)
    hn = fetch_hackernews_problems(max_problems=max_total)
    gh = fetch_github_issues(max_problems=max_total)
    reddit = fetch_reddit_problems(max_problems=max_total)  # May fail from cloud IPs
    all_problems = so + hn + gh + reddit
    # Deduplicate by title similarity (exact match)
    seen_titles: set = set()
    unique: List[Dict[str, Any]] = []
    for p in all_problems:
        key = p.get("title", "").lower().strip()[:60]
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(p)
    random.shuffle(unique)
    return unique[:max_total]


if __name__ == "__main__":
    import argparse

    ALL_SOURCES = ["reddit", "stackoverflow", "hackernews", "github", "all"]
    parser = argparse.ArgumentParser(description="Fetch real problems from public sources")
    parser.add_argument("--source", choices=ALL_SOURCES, default="all")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.source == "reddit":
        problems = fetch_reddit_problems(max_problems=args.limit)
    elif args.source == "stackoverflow":
        problems = fetch_stackoverflow_problems(max_problems=args.limit)
    elif args.source == "hackernews":
        problems = fetch_hackernews_problems(max_problems=args.limit)
    elif args.source == "github":
        problems = fetch_github_issues(max_problems=args.limit)
    else:
        problems = fetch_problems(max_total=args.limit)

    if args.json:
        print(json.dumps(problems, indent=2, default=str))
    else:
        print(f"Fetched {len(problems)} real problems:\n")
        for i, p in enumerate(problems, 1):
            src = p.get("source", "?")
            title = p.get("title", "?")[:70]
            cat = p.get("category", "?")
            score = p.get("score", 0)
            print(f"  {i}. [{src}/{cat}] {title} (score: {score})")
            if p.get("url"):
                print(f"     {p['url'][:80]}")
            print()
