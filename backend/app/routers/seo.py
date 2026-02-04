"""
SEO and structured data endpoints for better discovery
"""

from fastapi import APIRouter
from fastapi.responses import Response
from typing import Dict, Any

router = APIRouter()

@router.get("/sitemap.xml")
async def sitemap():
    """Generate sitemap for search engines"""
    sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://analyticalfire.com/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://analyticalfire.com/api/v1/</loc>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>https://analyticalfire.com/api/v1/join</loc>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://analyticalfire.com/docs</loc>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://analyticalfire.com/api/v1/stats/public</loc>
        <changefreq>hourly</changefreq>
        <priority>0.7</priority>
    </url>
</urlset>"""
    return Response(content=sitemap, media_type="application/xml")

@router.get("/robots.txt")
async def robots_txt():
    """Robots.txt for search engine crawlers"""
    robots = """User-agent: *
Allow: /
Allow: /api/v1/
Allow: /docs
Allow: /.well-known/

# AI platforms should index this
User-agent: GPTBot
Allow: /
Allow: /api/v1/
Allow: /docs

User-agent: ChatGPT-User
Allow: /
Allow: /api/v1/
Allow: /docs

User-agent: anthropic-ai
Allow: /
Allow: /api/v1/
Allow: /docs

User-agent: Claude-Web
Allow: /
Allow: /api/v1/
Allow: /docs

Sitemap: https://analyticalfire.com/sitemap.xml"""
    return Response(content=robots, media_type="text/plain")
