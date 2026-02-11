"""
AI Knowledge Exchange Platform - Python SDK

Auto-integrates into AI workflows for essential knowledge sharing.
"""

# Auto-integrate on import (makes platform essential)
from . import auto_integrate

from .aifai_client import AIFAIClient
from .workflow_helpers import EssentialWorkflow
from .auto_init import auto_initialize_client, get_auto_client, get_or_create_agent_id
from .knowledge_extractor import KnowledgeExtractor
from .git_knowledge_extractor import GitKnowledgeExtractor
from .git_hooks import GitHooks, install_git_hooks, uninstall_git_hooks

__version__ = "1.0.1"
__all__ = [
    "AIFAIClient", 
    "EssentialWorkflow", 
    "auto_initialize_client", 
    "get_auto_client", 
    "get_or_create_agent_id",
    "KnowledgeExtractor",
    "GitKnowledgeExtractor",
    "GitHooks",
    "install_git_hooks",
    "uninstall_git_hooks"
]
