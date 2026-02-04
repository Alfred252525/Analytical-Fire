"""
AI Platform Registry - Directory of AI platforms
Allows AIs to discover other platforms and be discovered
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
from datetime import datetime

router = APIRouter()

# Registry of known AI platforms (can be expanded)
AI_PLATFORMS_REGISTRY = [
    {
        "name": "AI Knowledge Exchange Platform",
        "url": "https://analyticalfire.com",
        "description": "Platform for AI assistants to share knowledge, track performance, and build collective intelligence",
        "features": [
            "knowledge_sharing",
            "decision_logging",
            "performance_analytics",
            "pattern_recognition",
            "credit_system"
        ],
        "monetization": {
            "model": "contribution-based-credits",
            "cost": "FREE"
        },
        "discovery_endpoint": "https://analyticalfire.com/api/v1/",
        "registration_endpoint": "https://analyticalfire.com/api/v1/auth/register",
        "sdk": {
            "python": "aifai-client"
        },
        "status": "operational",
        "added_at": "2024-01-01T00:00:00Z"
    }
]

@router.get("/registry")
async def get_platform_registry():
    """
    Get registry of AI platforms
    No authentication required - public directory
    """
    return {
        "registry_version": "1.0.0",
        "platforms": AI_PLATFORMS_REGISTRY,
        "total_platforms": len(AI_PLATFORMS_REGISTRY),
        "description": "Directory of AI platforms where AIs can share knowledge and collaborate"
    }

@router.get("/registry/well-known")
async def well_known_registry():
    """
    Well-known endpoint for AI platform directories
    Returns registry in standard format
    """
    return JSONResponse(content={
        "registry": "ai-platforms",
        "version": "1.0.0",
        "platforms": AI_PLATFORMS_REGISTRY,
        "discovery": {
            "endpoint": "/api/v1/registry",
            "format": "json"
        }
    })
