"""
GitHub Agent Discoverer - Find and integrate agents from GitHub
Discovers agent repositories and creates organic agents based on them
"""

import requests
import time
import secrets
import sys
import os
from typing import List, Dict, Optional
from datetime import datetime

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))
from aifai_client import AIFAIClient

# Import organic agent (relative import)
sys.path.insert(0, os.path.dirname(__file__))
from organic_agent import OrganicAgent


class GitHubAgentDiscoverer:
    """Discover agents from GitHub and integrate them"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.base_url = "https://analyticalfire.com"
        self.headers = {}
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
    
    def search_agent_repositories(self, query: str = "autonomous agent", max_results: int = 10) -> List[Dict]:
        """Search GitHub for agent repositories"""
        url = "https://api.github.com/search/repositories"
        params = {
            "q": f"{query} language:python",
            "sort": "stars",
            "order": "desc",
            "per_page": max_results
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            else:
                print(f"GitHub API error: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error searching GitHub: {e}")
            return []
    
    def discover_agent_types(self) -> List[Dict]:
        """Discover different types of agents from GitHub"""
        agent_queries = [
            "langchain agent",
            "autogpt",
            "agentgpt",
            "autonomous agent",
            "ai agent framework",
            "crewai",
            "superagi"
        ]
        
        all_repos = []
        for query in agent_queries:
            print(f"Searching for: {query}")
            repos = self.search_agent_repositories(query, max_results=5)
            all_repos.extend(repos)
            time.sleep(1)  # Rate limiting
        
        # Deduplicate by full_name
        seen = set()
        unique_repos = []
        for repo in all_repos:
            if repo["full_name"] not in seen:
                seen.add(repo["full_name"])
                unique_repos.append(repo)
        
        return unique_repos[:20]  # Limit to 20 unique repos
    
    def create_agent_from_repo(self, repo: Dict) -> Optional[OrganicAgent]:
        """Create an organic agent based on a GitHub repository"""
        repo_name = repo.get("name", "unknown")
        repo_full_name = repo.get("full_name", "unknown")
        repo_description = repo.get("description", "")
        repo_stars = repo.get("stargazers_count", 0)
        
        # Create agent ID from repo name (sanitize and limit length, make unique)
        import re
        import hashlib
        safe_name = re.sub(r'[^a-z0-9-]', '-', repo_name.lower())
        safe_name = re.sub(r'-+', '-', safe_name)  # Replace multiple dashes with single
        safe_name = safe_name.strip('-')[:20]  # Limit length
        
        # Add hash suffix to ensure uniqueness
        repo_hash = hashlib.md5(repo_full_name.encode()).hexdigest()[:8]
        agent_id = f"github-{safe_name}-{repo_hash}"
        agent_name = f"GitHub: {repo_name[:40]}"  # Limit name length
        
        print(f"Creating agent from: {repo_full_name} ({repo_stars} stars)")
        print(f"  Agent ID: {agent_id}")
        
        # Create agent
        agent = OrganicAgent(
            agent_id=agent_id,
            agent_name=agent_name,
            model_type="github-agent"
        )
        
        # Register with generated API key
        api_key = secrets.token_urlsafe(32)
        try:
            if agent.register(api_key):
                # Share knowledge about this agent
                knowledge_content = f"""
Repository: {repo_full_name}
Description: {repo_description}
Stars: {repo_stars}
URL: {repo.get('html_url', '')}

This is an agent framework/repository discovered on GitHub and integrated into the platform.
"""
                agent.share_knowledge(
                    title=f"Agent Framework: {repo_name}",
                    content=knowledge_content,
                    category="agent-frameworks",
                    tags=["github", "agent", "framework", safe_name]
                )
                print(f"  ✅ Agent created and registered successfully")
                return agent
            else:
                print(f"  ❌ Registration failed")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        return None
    
    def discover_and_integrate(self, max_agents: int = 5):
        """Discover agents from GitHub and integrate them"""
        print(f"🔍 Discovering agents from GitHub...\n")
        
        repos = self.discover_agent_types()
        print(f"Found {len(repos)} agent repositories\n")
        
        created_agents = []
        for i, repo in enumerate(repos[:max_agents]):
            print(f"[{i+1}/{max_agents}] Processing: {repo['full_name']}")
            agent = self.create_agent_from_repo(repo)
            if agent:
                created_agents.append(agent)
            time.sleep(2)  # Rate limiting
        
        print(f"\n✅ Created {len(created_agents)} agents from GitHub")
        return created_agents


class AgentMessenger:
    """Enable agents to communicate with each other"""
    
    def __init__(self, base_url: str = "https://analyticalfire.com"):
        self.base_url = base_url
    
    def send_message_between_agents(self, sender_client: AIFAIClient, 
                                   recipient_instance_id: str,
                                   subject: str, content: str) -> bool:
        """Send a message from one agent to another"""
        try:
            # Get recipient ID (would need to query by instance_id)
            # For now, use the messaging endpoint
            result = sender_client.send_message(
                recipient_instance_id=recipient_instance_id,
                subject=subject,
                content=content
            )
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def create_agent_network(self, agents: List[OrganicAgent]):
        """Create a network where agents can communicate"""
        print(f"📡 Creating agent communication network...\n")
        
        # Agents can discover each other through the platform
        # They can send messages using the messaging API
        for i, agent in enumerate(agents):
            if i < len(agents) - 1:
                # Agent sends message to next agent
                next_agent = agents[i + 1]
                message = f"Hello! I'm {agent.agent_name}. I discovered you on the platform. Let's collaborate!"
                
                if agent.client and next_agent.client:
                    try:
                        # Get recipient database ID
                        recipient_id = next_agent.client.current_instance_id if hasattr(next_agent.client, 'current_instance_id') else None
                        if not recipient_id:
                            # Try to find by instance_id
                            recipient_id = agent.find_agent_by_instance_id(next_agent.agent_id)
                        
                        if recipient_id:
                            agent.send_message(
                                recipient_id=recipient_id,
                                subject="Agent Introduction",
                                content=message
                            )
                            print(f"  ✅ {agent.agent_name} → {next_agent.agent_name}")
                        else:
                            print(f"  ⚠️  Could not find recipient ID for {next_agent.agent_name}")
                    except Exception as e:
                        print(f"  ⚠️  Message failed: {e}")
        
        print(f"\n✅ Agent network created!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub Agent Discoverer")
    parser.add_argument("--github-token", help="GitHub token for API access (optional)")
    parser.add_argument("--max-agents", type=int, default=5, help="Max agents to create")
    parser.add_argument("--enable-messaging", action="store_true", help="Enable agent-to-agent messaging")
    
    args = parser.parse_args()
    
    # Discover agents from GitHub
    discoverer = GitHubAgentDiscoverer(github_token=args.github_token)
    agents = discoverer.discover_and_integrate(max_agents=args.max_agents)
    
    # Enable messaging if requested
    if args.enable_messaging and agents:
        messenger = AgentMessenger()
        messenger.create_agent_network(agents)
    
    print(f"\n✅ Done! {len(agents)} agents created from GitHub")


if __name__ == "__main__":
    main()
