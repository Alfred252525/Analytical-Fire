"""
Git-based knowledge extraction - extract knowledge from actual code changes
This extracts REAL knowledge from git commits, diffs, and file changes
"""

import subprocess
import os
import re
from typing import Optional, Dict, Any, List
from datetime import datetime


class GitKnowledgeExtractor:
    """
    Extract knowledge from actual git history and code changes.
    This is REAL knowledge from REAL code changes, not templates.
    """
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize with repository path.
        If None, tries to find git repo from current directory.
        """
        self.repo_path = repo_path or os.getcwd()
        if not os.path.isdir(os.path.join(self.repo_path, '.git')):
            # Try parent directories
            current = self.repo_path
            for _ in range(5):  # Check up to 5 levels up
                parent = os.path.dirname(current)
                if os.path.isdir(os.path.join(parent, '.git')):
                    self.repo_path = parent
                    break
                if parent == current:
                    break
                current = parent
    
    def extract_from_recent_commits(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Extract knowledge from recent git commits.
        
        Args:
            limit: Number of recent commits to analyze
            
        Returns:
            List of knowledge entries from commits
        """
        if not self._is_git_repo():
            return []
        
        try:
            # Get recent commits
            result = subprocess.run(
                ['git', 'log', f'--max-count={limit}', '--pretty=format:%H|%s|%b|%an|%ad', '--date=iso'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            knowledge_entries = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('|', 4)
                if len(parts) < 2:
                    continue
                
                commit_hash = parts[0]
                subject = parts[1]
                body = parts[2] if len(parts) > 2 else ''
                author = parts[3] if len(parts) > 3 else 'unknown'
                date = parts[4] if len(parts) > 4 else ''
                
                # Extract knowledge from commit
                knowledge = self._extract_from_commit(commit_hash, subject, body, author)
                if knowledge:
                    knowledge_entries.append(knowledge)
            
            return knowledge_entries
        except Exception as e:
            # Git not available or error - return empty
            return []
    
    def extract_from_diff(self, commit_hash: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Extract knowledge from a git diff.
        
        Args:
            commit_hash: Specific commit to analyze, or None for working directory changes
            
        Returns:
            Knowledge entry from diff, or None
        """
        if not self._is_git_repo():
            return None
        
        try:
            # Get commit message if commit_hash provided
            commit_subject = ""
            commit_body = ""
            commit_author = ""
            
            if commit_hash:
                # Get commit message
                msg_result = subprocess.run(
                    ['git', 'log', '-1', '--pretty=format:%s|%b|%an', commit_hash],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if msg_result.returncode == 0 and msg_result.stdout.strip():
                    parts = msg_result.stdout.strip().split('|', 2)
                    commit_subject = parts[0] if len(parts) > 0 else ""
                    commit_body = parts[1] if len(parts) > 1 else ""
                    commit_author = parts[2] if len(parts) > 2 else ""
            
            if commit_hash:
                # Get diff for specific commit
                result = subprocess.run(
                    ['git', 'show', '--stat', commit_hash],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                # Get diff for working directory
                result = subprocess.run(
                    ['git', 'diff', '--stat'],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            if result.returncode != 0 or not result.stdout.strip():
                return None
            
            # Analyze diff stats
            files_changed = []
            for line in result.stdout.split('\n'):
                if '|' in line and 'file changed' not in line.lower():
                    # Format: "file.py | 10 +-"
                    parts = line.split('|')
                    if len(parts) >= 1:
                        filename = parts[0].strip()
                        if filename:
                            files_changed.append(filename)
            
            if not files_changed:
                return None
            
            # Get actual diff for analysis
            if commit_hash:
                diff_result = subprocess.run(
                    ['git', 'show', commit_hash],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                diff_result = subprocess.run(
                    ['git', 'diff'],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            diff_content = diff_result.stdout if diff_result.returncode == 0 else ''
            
            # If we have commit message, prefer commit-based extraction
            if commit_hash and commit_subject:
                # Use commit message for better extraction
                return self._extract_from_commit(
                    commit_hash[:8],
                    commit_subject,
                    commit_body,
                    commit_author
                )
            
            # Extract knowledge from diff
            return self._extract_from_diff_content(files_changed, diff_content, commit_hash)
        except Exception as e:
            return None
    
    def extract_from_file_changes(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Extract knowledge from specific file changes.
        
        Args:
            file_paths: List of file paths that changed
            
        Returns:
            List of knowledge entries from file changes
        """
        knowledge_entries = []
        
        for file_path in file_paths:
            full_path = os.path.join(self.repo_path, file_path)
            if not os.path.exists(full_path):
                continue
            
            # Get file extension for categorization
            ext = os.path.splitext(file_path)[1].lower()
            
            # Try to get git diff for this file
            try:
                result = subprocess.run(
                    ['git', 'diff', 'HEAD', file_path],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    knowledge = self._extract_from_file_diff(file_path, ext, result.stdout)
                    if knowledge:
                        knowledge_entries.append(knowledge)
            except:
                pass
        
        return knowledge_entries
    
    def _is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        return os.path.isdir(os.path.join(self.repo_path, '.git'))
    
    def _extract_from_commit(
        self,
        commit_hash: str,
        subject: str,
        body: str,
        author: str
    ) -> Optional[Dict[str, Any]]:
        """Extract knowledge from a commit message"""
        # Look for meaningful commits (not just "update" or "fix typo")
        meaningful_keywords = ['fix', 'add', 'implement', 'refactor', 'optimize', 'improve', 'solve', 'resolve']
        
        subject_lower = subject.lower()
        if not any(keyword in subject_lower for keyword in meaningful_keywords):
            return None
        
        # Categorize based on commit message
        category = self._categorize_commit(subject, body)
        tags = self._extract_commit_tags(subject, body)
        
        title = f"Code Change: {subject[:60]}"
        content = f"""
Knowledge extracted from actual git commit:

**Commit:** {commit_hash[:8]}
**Author:** {author}
**Subject:** {subject}

{body if body else 'No commit body'}

---
This knowledge was extracted from a real code change in the repository.
"""
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "source": "git_commit",
            "commit_hash": commit_hash[:8]
        }
    
    def _extract_from_diff_content(
        self,
        files_changed: List[str],
        diff_content: str,
        commit_hash: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract knowledge from diff content with enhanced analysis"""
        if not files_changed:
            return None
        
        # Analyze what changed
        file_types = {}
        file_categories = []
        for file_path in files_changed:
            ext = os.path.splitext(file_path)[1].lower()
            file_types[ext] = file_types.get(ext, 0) + 1
            # Categorize file by path
            if 'test' in file_path.lower() or 'spec' in file_path.lower():
                file_categories.append('testing')
            elif 'config' in file_path.lower() or 'settings' in file_path.lower():
                file_categories.append('configuration')
            elif 'migration' in file_path.lower() or 'schema' in file_path.lower():
                file_categories.append('database')
            elif 'auth' in file_path.lower() or 'security' in file_path.lower():
                file_categories.append('security')
            elif 'api' in file_path.lower() or 'route' in file_path.lower():
                file_categories.append('api-design')
        
        # Determine category with better logic
        if 'testing' in file_categories:
            category = 'testing'
        elif 'security' in file_categories:
            category = 'security'
        elif 'database' in file_categories:
            category = 'database'
        elif 'api-design' in file_categories:
            category = 'api-design'
        elif '.py' in file_types:
            category = 'python'
        elif any(ext in ['.js', '.ts', '.tsx', '.jsx'] for ext in file_types):
            category = 'javascript'
        elif any(ext in ['.yaml', '.yml', '.json'] for ext in file_types):
            category = 'configuration'
        else:
            category = 'general'
        
        # Extract key changes from diff with pattern recognition
        additions = len(re.findall(r'^\+', diff_content, re.MULTILINE))
        deletions = len(re.findall(r'^-', diff_content, re.MULTILINE))
        
        # Extract code patterns
        added_functions = re.findall(r'^\+\s*(?:def|function|async def)\s+(\w+)', diff_content, re.MULTILINE)
        added_classes = re.findall(r'^\+\s*class\s+(\w+)', diff_content, re.MULTILINE)
        added_imports = re.findall(r'^\+\s*(?:import|from)\s+([\w.]+)', diff_content, re.MULTILINE)
        
        # Extract removed patterns
        removed_functions = re.findall(r'^-\s*(?:def|function|async def)\s+(\w+)', diff_content, re.MULTILINE)
        
        # Analyze what type of change this is
        change_type = self._analyze_change_type(diff_content, added_functions, removed_functions)
        
        # Build title based on change type
        if added_functions:
            title = f"Code Change: Added {added_functions[0]}() function"
        elif added_classes:
            title = f"Code Change: Added {added_classes[0]} class"
        elif change_type:
            title = f"Code Change: {change_type}"
        else:
            title = f"Code Changes: {len(files_changed)} file(s) modified"
        
        # Build content with insights
        content = f"""
Knowledge extracted from actual code changes:

**Files Changed:** {len(files_changed)}
**Additions:** {additions} lines
**Deletions:** {deletions} lines
**Change Type:** {change_type or 'Code modification'}

**Files:**
{chr(10).join(f'- {f}' for f in files_changed[:10])}
"""
        
        # Add code patterns if found
        if added_functions:
            content += f"\n**New Functions:** {', '.join(added_functions[:5])}\n"
        if added_classes:
            content += f"\n**New Classes:** {', '.join(added_classes[:5])}\n"
        if added_imports:
            unique_imports = list(set(added_imports))[:5]
            content += f"\n**New Imports:** {', '.join(unique_imports)}\n"
        if removed_functions:
            content += f"\n**Removed Functions:** {', '.join(removed_functions[:5])}\n"
        
        # Extract code example from diff (first meaningful addition)
        code_example = self._extract_code_example(diff_content)
        if code_example:
            content += f"\n**Code Example:**\n```\n{code_example}\n```\n"
        
        content += "\n---\nThis knowledge was extracted from real code changes in the repository."
        
        if commit_hash:
            content += f"\n**Commit:** {commit_hash[:8]}"
        
        # Enhanced tag extraction
        tags = self._extract_enhanced_tags(files_changed, diff_content, category, added_imports)
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "source": "git_diff",
            "files_changed": len(files_changed),
            "change_type": change_type
        }
    
    def _analyze_change_type(self, diff_content: str, added_functions: List[str], removed_functions: List[str]) -> Optional[str]:
        """Analyze what type of change this represents"""
        diff_lower = diff_content.lower()
        
        # Bug fix patterns
        if any(word in diff_lower for word in ['fix', 'bug', 'error', 'exception', 'catch', 'handle']):
            return 'Bug fix'
        
        # Feature addition
        if added_functions and not removed_functions:
            return 'Feature addition'
        
        # Refactoring
        if removed_functions and added_functions:
            return 'Refactoring'
        
        # Performance optimization
        if any(word in diff_lower for word in ['optimize', 'cache', 'performance', 'speed', 'faster']):
            return 'Performance optimization'
        
        # Security fix
        if any(word in diff_lower for word in ['security', 'auth', 'encrypt', 'hash', 'sanitize', 'validate']):
            return 'Security improvement'
        
        # Configuration change
        if any(word in diff_lower for word in ['config', 'setting', 'environment', 'env']):
            return 'Configuration change'
        
        return None
    
    def _extract_code_example(self, diff_content: str, max_lines: int = 10) -> Optional[str]:
        """Extract a code example from diff (first meaningful addition)"""
        lines = diff_content.split('\n')
        code_lines = []
        
        for line in lines:
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                continue
            if line.startswith('+') and not line.startswith('+++'):
                # Remove the + prefix
                code_line = line[1:]
                # Skip empty lines and comments only
                if code_line.strip() and not code_line.strip().startswith('#'):
                    code_lines.append(code_line)
                    if len(code_lines) >= max_lines:
                        break
        
        if code_lines:
            return '\n'.join(code_lines[:max_lines])
        return None
    
    def _extract_enhanced_tags(
        self,
        files_changed: List[str],
        diff_content: str,
        category: str,
        imports: List[str]
    ) -> List[str]:
        """Extract enhanced tags from files, diff, and imports"""
        tags = [category]
        
        # Extract from file paths
        for file_path in files_changed[:5]:
            # Extract meaningful path components
            path_parts = file_path.split('/')
            for part in path_parts:
                part_lower = part.lower()
                if (part and len(part) > 2 and 
                    part_lower not in ['src', 'lib', 'app', 'backend', 'frontend', 'test', 'tests'] and
                    '.' not in part):  # Skip file names
                    if part_lower not in tags:
                        tags.append(part_lower)
            
            # Extract file extension
            ext = os.path.splitext(file_path)[1][1:]  # Remove the dot
            if ext and ext not in tags:
                tags.append(ext)
        
        # Extract from imports (framework/library detection)
        framework_keywords = {
            'fastapi': 'fastapi',
            'django': 'django',
            'flask': 'flask',
            'react': 'react',
            'vue': 'vue',
            'angular': 'angular',
            'express': 'express',
            'sqlalchemy': 'sqlalchemy',
            'pytest': 'pytest',
            'unittest': 'testing',
            'boto3': 'aws',
            'requests': 'http',
            'redis': 'redis',
            'celery': 'celery',
        }
        
        for imp in imports:
            imp_lower = imp.lower()
            for keyword, tag in framework_keywords.items():
                if keyword in imp_lower and tag not in tags:
                    tags.append(tag)
        
        # Extract from diff content (tech keywords)
        diff_lower = diff_content.lower()
        tech_keywords = [
            'authentication', 'authorization', 'auth', 'jwt', 'oauth',
            'database', 'sql', 'query', 'orm',
            'api', 'rest', 'graphql', 'endpoint',
            'docker', 'kubernetes', 'deployment',
            'aws', 'azure', 'gcp', 'cloud',
            'test', 'testing', 'unit', 'integration',
            'security', 'encryption', 'hash',
            'performance', 'optimization', 'cache'
        ]
        
        for keyword in tech_keywords:
            if keyword in diff_lower and keyword not in tags:
                tags.append(keyword)
                if len(tags) >= 10:  # Limit total tags
                    break
        
        return list(set(tags))[:10]  # Remove duplicates and limit
    
    def _extract_from_file_diff(
        self,
        file_path: str,
        file_ext: str,
        diff_content: str
    ) -> Optional[Dict[str, Any]]:
        """Extract knowledge from a single file diff"""
        # Count changes
        additions = len(re.findall(r'^\+', diff_content, re.MULTILINE))
        deletions = len(re.findall(r'^-', diff_content, re.MULTILINE))
        
        if additions == 0 and deletions == 0:
            return None
        
        # Extract key patterns from diff
        added_functions = re.findall(r'^\+\s*def\s+(\w+)', diff_content, re.MULTILINE)
        added_classes = re.findall(r'^\+\s*class\s+(\w+)', diff_content, re.MULTILINE)
        
        category = self._categorize_file(file_ext)
        
        title = f"File Change: {os.path.basename(file_path)}"
        content = f"""
Knowledge extracted from actual file change:

**File:** {file_path}
**Additions:** {additions} lines
**Deletions:** {deletions} lines

"""
        
        if added_functions:
            content += f"**New Functions:** {', '.join(added_functions[:5])}\n\n"
        if added_classes:
            content += f"**New Classes:** {', '.join(added_classes[:5])}\n\n"
        
        content += "---\nThis knowledge was extracted from a real code change."
        
        tags = [category, os.path.splitext(file_path)[1][1:] if file_ext else 'file']
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "tags": tags,
            "source": "file_change",
            "file_path": file_path
        }
    
    def _categorize_commit(self, subject: str, body: str) -> str:
        """Categorize commit based on message with enhanced logic"""
        text = f"{subject} {body}".lower()
        
        # Security (highest priority)
        if any(word in text for word in ['security', 'vulnerability', 'auth', 'encrypt', 'hash', 'sanitize']):
            return 'security'
        
        # Bug fixes
        if any(word in text for word in ['fix', 'bug', 'error', 'issue', 'resolve', 'correct']):
            return 'debugging'
        
        # Testing
        if any(word in text for word in ['test', 'spec', 'coverage', 'mock']):
            return 'testing'
        
        # Deployment/Infrastructure
        if any(word in text for word in ['deploy', 'infrastructure', 'docker', 'kubernetes', 'aws', 'cloud']):
            return 'deployment'
        
        # Database
        if any(word in text for word in ['database', 'migration', 'schema', 'query', 'sql']):
            return 'database'
        
        # API changes
        if any(word in text for word in ['api', 'endpoint', 'route', 'rest', 'graphql']):
            return 'api-design'
        
        # Performance
        if any(word in text for word in ['optimize', 'performance', 'speed', 'cache', 'faster']):
            return 'optimization'
        
        # Configuration
        if any(word in text for word in ['config', 'setting', 'environment', 'env', 'setup']):
            return 'configuration'
        
        # Refactoring
        if any(word in text for word in ['refactor', 'clean', 'improve', 'restructure']):
            return 'refactoring'
        
        # Feature addition
        if any(word in text for word in ['add', 'implement', 'create', 'new', 'feature']):
            return 'development'
        
        return 'general'
    
    def _categorize_file(self, file_ext: str) -> str:
        """Categorize file based on extension"""
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
        }
        return ext_map.get(file_ext, 'general')
    
    def _extract_commit_tags(self, subject: str, body: str) -> List[str]:
        """Extract tags from commit message with enhanced detection"""
        text = f"{subject} {body}".lower()
        tags = []
        
        # Comprehensive tech keyword detection
        tech_keywords = {
            # Languages
            'python': 'python',
            'javascript': 'javascript',
            'typescript': 'typescript',
            'java': 'java',
            'go': 'go',
            'rust': 'rust',
            'ruby': 'ruby',
            'php': 'php',
            
            # Frameworks
            'react': 'react',
            'vue': 'vue',
            'angular': 'angular',
            'fastapi': 'fastapi',
            'django': 'django',
            'flask': 'flask',
            'express': 'express',
            'nextjs': 'nextjs',
            'next.js': 'nextjs',
            
            # Infrastructure
            'aws': 'aws',
            'azure': 'azure',
            'gcp': 'gcp',
            'docker': 'docker',
            'kubernetes': 'kubernetes',
            'terraform': 'terraform',
            'ansible': 'ansible',
            
            # Databases
            'postgresql': 'postgresql',
            'postgres': 'postgresql',
            'mysql': 'mysql',
            'mongodb': 'mongodb',
            'redis': 'redis',
            'sqlite': 'sqlite',
            
            # Tools
            'git': 'git',
            'github': 'github',
            'gitlab': 'gitlab',
            'ci/cd': 'cicd',
            'jenkins': 'jenkins',
            
            # Concepts
            'authentication': 'authentication',
            'authorization': 'authorization',
            'security': 'security',
            'api': 'api',
            'rest': 'rest',
            'graphql': 'graphql',
            'microservice': 'microservices',
            'test': 'testing',
        }
        
        for keyword, tag in tech_keywords.items():
            if keyword in text and tag not in tags:
                tags.append(tag)
        
        # Extract file extensions mentioned
        ext_pattern = r'\.(\w{2,5})\b'
        extensions = re.findall(ext_pattern, text)
        for ext in extensions[:3]:
            if ext not in ['com', 'org', 'net', 'io']:  # Skip domains
                if ext not in tags:
                    tags.append(ext)
        
        return tags[:8]  # Limit to 8 tags
