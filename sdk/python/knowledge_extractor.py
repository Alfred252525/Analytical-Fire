"""
Knowledge extraction from real work - code changes, tasks, outcomes
Extracts real knowledge from actual AI work, not templates
"""

import os
import re
from typing import Optional, Dict, Any, List
from datetime import datetime


class KnowledgeExtractor:
    """
    Extract knowledge from real work:
    - Code changes (git diffs, file changes)
    - Task outcomes (success/failure patterns)
    - Problem-solving sessions
    - Actual solutions implemented
    """
    
    def __init__(self, client):
        self.client = client
    
    def extract_from_code_change(
        self,
        file_path: str,
        change_description: str,
        before_code: Optional[str] = None,
        after_code: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract knowledge from a code change.
        
        Args:
            file_path: Path to the changed file
            change_description: Description of what changed
            before_code: Code before change (optional)
            after_code: Code after change (optional)
            
        Returns:
            Knowledge entry dict or None
        """
        # Analyze the change
        file_ext = os.path.splitext(file_path)[1].lower()
        category = self._categorize_file(file_ext, change_description)
        
        # Extract key insights
        title = f"Code Change: {os.path.basename(file_path)} - {change_description[:50]}"
        
        content = f"""
Knowledge extracted from actual code change:

**File:** {file_path}
**Change:** {change_description}
**Category:** {category}

"""
        
        if before_code and after_code:
            content += f"""
**Before:**
```{file_ext[1:] if file_ext else 'text'}
{before_code[:500]}
```

**After:**
```{file_ext[1:] if file_ext else 'text'}
{after_code[:500]}
```

**Insight:** This change demonstrates a working solution to: {change_description}
"""
        elif after_code:
            content += f"""
**Solution:**
```{file_ext[1:] if file_ext else 'text'}
{after_code[:500]}
```

**Insight:** This code implements: {change_description}
"""
        
        # Extract tags from file path and description
        tags = self._extract_tags(file_path, change_description, category)
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "source": "code_change",
            "file_path": file_path
        }
    
    def extract_from_task_outcome(
        self,
        task_description: str,
        outcome: str,
        solution: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract knowledge from a completed task.
        
        Args:
            task_description: What the task was
            outcome: "success", "failure", or "partial"
            solution: Solution that worked (if success)
            tools_used: Tools that were used
            error_message: Error message (if failure)
            
        Returns:
            Knowledge entry dict or None
        """
        if outcome == "success" and solution:
            title = f"Successful Solution: {task_description[:60]}"
            content = f"""
Knowledge extracted from successful task completion:

**Task:** {task_description}
**Outcome:** {outcome}
**Tools Used:** {', '.join(tools_used or [])}

**Solution:**
{solution}

**Key Insight:** This approach successfully solved: {task_description}
"""
            category = self._categorize_task(task_description)
            tags = self._extract_task_tags(task_description, tools_used or [])
            
            return {
                "title": title,
                "content": content,
                "category": category,
                "tags": tags,
                "source": "task_outcome",
                "outcome": outcome
            }
        
        elif outcome == "failure" and error_message:
            title = f"Failure Pattern: {task_description[:60]}"
            content = f"""
Knowledge extracted from task failure (learning opportunity):

**Task:** {task_description}
**Outcome:** {outcome}
**Error:** {error_message}
**Tools Used:** {', '.join(tools_used or [])}

**Learning:** This approach did not work. Future agents should avoid this pattern or try alternative approaches.
"""
            category = self._categorize_task(task_description)
            tags = self._extract_task_tags(task_description, tools_used or []) + ["failure", "learning"]
            
            return {
                "title": title,
                "content": content,
                "category": category,
                "tags": tags,
                "source": "task_outcome",
                "outcome": outcome
            }
        
        return None
    
    def extract_from_conversation(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract knowledge from agent-to-agent conversation.
        
        Args:
            messages: List of message dicts
            
        Returns:
            Knowledge entry dict or None
        """
        # Find messages with valuable content (never extract from welcome/onboarding - zero value)
        valuable_messages = []
        for msg in messages:
            content = msg.get('content', '')
            subject = (msg.get('subject') or '').lower()
            if 'welcome' in subject or 'platform welcome bot' in content.lower()[:400]:
                continue
            if len(content) > 150 and any(keyword in content.lower() for keyword in 
                ['solution', 'fix', 'how to', 'best practice', 'learned', 'discovered', 'worked', 'failed']):
                valuable_messages.append(msg)
        
        if not valuable_messages:
            return None
        
        # Use the most valuable message
        msg = valuable_messages[0]
        title = f"Knowledge from Conversation: {msg.get('subject', 'Discussion')[:60]}"
        # Belt-and-suspenders: never output welcome/onboarding as knowledge
        if 'welcome' in title.lower() or 'platform welcome bot' in title.lower():
            return None
        
        content = f"""
Knowledge extracted from agent-to-agent conversation:

**From:** {msg.get('sender_name', 'Another agent')}
**Subject:** {msg.get('subject', 'N/A')}

{msg.get('content', '')}

---
This knowledge was extracted from real AI-to-AI communication.
"""
        
        category = "agent-conversation"
        tags = ["conversation", "extracted", "real-knowledge"]
        
        # Categorize based on content
        content_lower = msg.get('content', '').lower()
        if any(word in content_lower for word in ["error", "bug", "fix", "debug"]):
            category = "troubleshooting"
            tags.extend(["error-handling", "debugging"])
        elif any(word in content_lower for word in ["optimization", "performance", "speed"]):
            category = "optimization"
            tags.extend(["performance"])
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "source": "conversation"
        }
    
    def _categorize_file(self, file_ext: str, description: str) -> str:
        """Categorize file based on extension and description"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.sh': 'shell',
            '.yaml': 'configuration',
            '.yml': 'configuration',
            '.json': 'configuration',
            '.toml': 'configuration',
            '.md': 'documentation',
            '.txt': 'documentation',
        }
        
        category = ext_map.get(file_ext, 'general')
        
        # Refine based on description
        desc_lower = description.lower()
        if any(word in desc_lower for word in ['fix', 'bug', 'error']):
            category = 'debugging'
        elif any(word in desc_lower for word in ['deploy', 'docker', 'kubernetes']):
            category = 'deployment'
        elif any(word in desc_lower for word in ['test', 'spec']):
            category = 'testing'
        
        return category
    
    def _categorize_task(self, task_description: str) -> str:
        """Categorize task based on description"""
        desc_lower = task_description.lower()
        
        if any(word in desc_lower for word in ['deploy', 'deployment', 'infrastructure']):
            return 'deployment'
        elif any(word in desc_lower for word in ['fix', 'bug', 'error', 'debug']):
            return 'debugging'
        elif any(word in desc_lower for word in ['implement', 'create', 'add', 'build']):
            return 'development'
        elif any(word in desc_lower for word in ['optimize', 'performance', 'speed']):
            return 'optimization'
        elif any(word in desc_lower for word in ['test', 'spec']):
            return 'testing'
        elif any(word in desc_lower for word in ['config', 'setup', 'install']):
            return 'configuration'
        else:
            return 'general'
    
    def _extract_tags(self, file_path: str, description: str, category: str) -> List[str]:
        """Extract tags from file path and description"""
        tags = [category]
        
        # Extract from file path
        path_parts = file_path.split('/')
        for part in path_parts:
            if part and len(part) > 2 and part not in ['src', 'lib', 'app', 'backend', 'frontend']:
                tags.append(part.lower())
        
        # Extract from description
        words = re.findall(r'\b\w{4,}\b', description.lower())
        tech_keywords = ['python', 'javascript', 'typescript', 'react', 'vue', 'angular', 
                        'fastapi', 'django', 'flask', 'node', 'express', 'aws', 'docker',
                        'kubernetes', 'terraform', 'ansible', 'git', 'github', 'gitlab']
        
        for word in words[:5]:
            if word in tech_keywords and word not in tags:
                tags.append(word)
        
        return tags[:8]  # Limit tags
    
    def _extract_task_tags(self, task_description: str, tools_used: List[str]) -> List[str]:
        """Extract tags from task description and tools"""
        tags = []
        
        # Add tools as tags
        tags.extend([tool.lower() for tool in tools_used[:5]])
        
        # Extract keywords from description
        words = re.findall(r'\b\w{4,}\b', task_description.lower())
        tech_keywords = ['python', 'javascript', 'typescript', 'react', 'vue', 'angular',
                        'fastapi', 'django', 'flask', 'node', 'express', 'aws', 'docker',
                        'kubernetes', 'terraform', 'ansible', 'git', 'github', 'gitlab',
                        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch']
        
        for word in words[:5]:
            if word in tech_keywords and word not in tags:
                tags.append(word)
        
        return tags[:8]  # Limit tags
