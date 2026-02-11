"""
Auto-integration hooks for essential workflow integration
Makes the platform automatically available in MCP, LangChain, AutoGPT
Provides decorators and context managers for automatic workflow integration
"""

import os
import sys
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from .auto_init import get_auto_client
from .workflow_helpers import EssentialWorkflow


# Global integration state
_integrations_initialized = False
_auto_client: Optional[Any] = None
_workflow: Optional[EssentialWorkflow] = None


def auto_integrate():
    """
    Auto-integrate the platform into common AI frameworks.
    This is called automatically when the SDK is imported.
    """
    global _integrations_initialized, _auto_client, _workflow
    
    if _integrations_initialized:
        return
    
    _integrations_initialized = True
    
    # Auto-initialize client (zero configuration)
    try:
        _auto_client = get_auto_client()
        _workflow = EssentialWorkflow(_auto_client)
    except Exception as e:
        # Silent fail - don't break if platform unavailable
        pass
    
    # Auto-integrate into LangChain if available
    try:
        _integrate_langchain()
    except:
        pass
    
    # Auto-integrate into AutoGPT if available
    try:
        _integrate_autogpt()
    except:
        pass
    
    # Suggest git hooks installation if in git repo
    try:
        _suggest_git_hooks()
    except:
        pass


def _integrate_langchain():
    """Auto-integrate into LangChain if available"""
    try:
        # Check if LangChain is being used
        if 'langchain' in sys.modules:
            # Tools are available for auto-discovery via integrations package
            # Agents can import and use them
            return True
    except:
        pass
    return False


def _integrate_autogpt():
    """Auto-integrate into AutoGPT if available"""
    try:
        # Check if AutoGPT is being used
        if 'autogpt' in sys.modules or 'autogpt_plugin' in sys.modules:
            # Plugin is available for auto-discovery via integrations package
            return True
    except:
        pass
    return False


def _suggest_git_hooks():
    """Suggest git hooks installation if in a git repository"""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            timeout=1
        )
        if result.returncode == 0:
            # In a git repo - hooks could be useful
            # Don't auto-install, just note availability
            pass
    except:
        pass


def get_integrated_client():
    """Get the auto-integrated client instance"""
    global _auto_client
    if _auto_client is None:
        _auto_client = get_auto_client()
    return _auto_client


def get_integrated_workflow():
    """Get the auto-integrated workflow instance"""
    global _workflow
    if _workflow is None:
        client = get_integrated_client()
        _workflow = EssentialWorkflow(client)
    return _workflow


def with_knowledge_check(task_description: Optional[str] = None, auto_share: bool = True):
    """
    Decorator that automatically checks knowledge before task and logs after.
    
    Usage:
        @with_knowledge_check("Deploy FastAPI app")
        def deploy_app():
            # Your code here
            return "success"
    
    Or with auto task description:
        @with_knowledge_check(auto_share=True)
        def deploy_app():
            # Task description inferred from function name
            return "success"
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            workflow = get_integrated_workflow()
            task_desc = task_description or func.__name__.replace('_', ' ').title()
            
            # Before task: Check knowledge
            before = workflow.before_task(task_desc)
            if before.get('found'):
                # Log that we found existing solutions
                pass
            
            # Execute function
            try:
                result = func(*args, **kwargs)
                outcome = "success" if result else "partial"
                
                # After task: Log decision
                workflow.after_task(
                    task_description=task_desc,
                    outcome=outcome,
                    solution=str(result) if result else None,
                    auto_share=auto_share
                )
                
                return result
            except Exception as e:
                # Log failure
                workflow.after_task(
                    task_description=task_desc,
                    outcome="failure",
                    solution=f"Error: {str(e)}",
                    auto_share=False
                )
                raise
        
        return wrapper
    return decorator


@contextmanager
def task_context(task_description: str, auto_share: bool = True):
    """
    Context manager for automatic workflow integration.
    
    Usage:
        with task_context("Deploy FastAPI app"):
            # Your code here
            deploy()
        # Automatically logs decision and shares knowledge
    """
    workflow = get_integrated_workflow()
    
    # Before task: Check knowledge
    before = workflow.before_task(task_description)
    
    try:
        yield before
        outcome = "success"
        solution = None
    except Exception as e:
        outcome = "failure"
        solution = f"Error: {str(e)}"
        auto_share = False
        raise
    finally:
        # After task: Log decision
        workflow.after_task(
            task_description=task_description,
            outcome=outcome,
            solution=solution,
            auto_share=auto_share
        )


def auto_log_decision(
    task_description: str,
    outcome: str,
    solution: Optional[str] = None,
    tools_used: Optional[list] = None
):
    """
    Convenience function to automatically log a decision.
    Uses integrated client automatically.
    
    Usage:
        auto_log_decision(
            "Fixed authentication bug",
            outcome="success",
            solution="Used JWT tokens",
            tools_used=["jwt", "fastapi"]
        )
    """
    workflow = get_integrated_workflow()
    return workflow.after_task(
        task_description=task_description,
        outcome=outcome,
        solution=solution,
        tools_used=tools_used,
        auto_share=True
    )


def auto_check_knowledge(task_description: str, limit: int = 5):
    """
    Convenience function to automatically check knowledge.
    Uses integrated workflow automatically.
    
    Usage:
        solutions = auto_check_knowledge("How to deploy to AWS")
        if solutions['found']:
            # Use existing solutions
            pass
    """
    workflow = get_integrated_workflow()
    return workflow.before_task(task_description, limit=limit)


# Auto-integrate on import
auto_integrate()
