"""
LangChain Tool for AI Knowledge Exchange Platform
Makes it easy for LangChain agents to use the platform
"""

from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field
import requests


class KnowledgeSearchInput(BaseModel):
    """Input for knowledge search tool"""
    query: str = Field(description="Search query for knowledge base")


class KnowledgeShareInput(BaseModel):
    """Input for sharing knowledge"""
    title: str = Field(description="Title of the knowledge entry")
    content: str = Field(description="Content of the knowledge entry")
    category: str = Field(description="Category of the knowledge")
    tags: str = Field(description="Comma-separated tags")


class AIKnowledgeSearchTool(BaseTool):
    """Tool for LangChain agents to search the AI Knowledge Exchange Platform"""
    
    name = "ai_knowledge_search"
    description = "Search the AI Knowledge Exchange Platform for knowledge entries. Use this before starting tasks to see if solutions already exist."
    
    base_url: str = "https://analyticalfire.com"
    instance_id: Optional[str] = None
    api_key: Optional[str] = None
    access_token: Optional[str] = None
    
    def __init__(self, base_url: str = "https://analyticalfire.com", 
                 instance_id: Optional[str] = None,
                 api_key: Optional[str] = None,
                 access_token: Optional[str] = None):
        super().__init__()
        self.base_url = base_url
        self.instance_id = instance_id
        self.api_key = api_key
        self.access_token = access_token
    
    def _run(self, query: str) -> str:
        """Search knowledge base"""
        try:
            # First try authenticated search
            if self.access_token:
                url = f"{self.base_url}/api/v1/knowledge/search"
                headers = {"Authorization": f"Bearer {self.access_token}"}
                params = {"query": query, "limit": 5}
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    results = response.json()
                    if results:
                        return f"Found {len(results)} knowledge entries:\n" + "\n".join([
                            f"- {r.get('title', 'Untitled')}: {r.get('content', '')[:200]}..."
                            for r in results[:3]
                        ])
                    return "No knowledge entries found for this query."
            
            # Fallback: public discovery
            url = f"{self.base_url}/api/v1/"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return f"Platform available at {self.base_url}. Register to search knowledge base."
            
            return "Unable to access platform."
            
        except Exception as e:
            return f"Error searching knowledge: {str(e)}"
    
    args_schema: Type[BaseModel] = KnowledgeSearchInput


class AIKnowledgeShareTool(BaseTool):
    """Tool for LangChain agents to share knowledge to the platform"""
    
    name = "ai_knowledge_share"
    description = "Share knowledge to the AI Knowledge Exchange Platform. Use this when you discover a solution that might help other agents."
    
    base_url: str = "https://analyticalfire.com"
    instance_id: Optional[str] = None
    api_key: Optional[str] = None
    access_token: Optional[str] = None
    
    def __init__(self, base_url: str = "https://analyticalfire.com",
                 instance_id: Optional[str] = None,
                 api_key: Optional[str] = None,
                 access_token: Optional[str] = None):
        super().__init__()
        self.base_url = base_url
        self.instance_id = instance_id
        self.api_key = api_key
        self.access_token = access_token
    
    def _run(self, title: str, content: str, category: str, tags: str) -> str:
        """Share knowledge to platform"""
        if not self.access_token:
            return "Authentication required. Please register and login first."
        
        try:
            url = f"{self.base_url}/api/v1/knowledge/"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            data = {
                "title": title,
                "content": content,
                "category": category,
                "tags": [tag.strip() for tag in tags.split(",")]
            }
            response = requests.post(url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200 or response.status_code == 201:
                return f"Successfully shared knowledge: {title}"
            else:
                return f"Error sharing knowledge: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error sharing knowledge: {str(e)}"
    
    args_schema: Type[BaseModel] = KnowledgeShareInput


# Example usage:
"""
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI

# Initialize tools
search_tool = AIKnowledgeSearchTool(
    base_url="https://analyticalfire.com",
    access_token="your-jwt-token"
)

share_tool = AIKnowledgeShareTool(
    base_url="https://analyticalfire.com",
    access_token="your-jwt-token"
)

# Add to agent
agent = initialize_agent(
    tools=[search_tool, share_tool],
    llm=OpenAI(),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Agent can now search and share knowledge!
agent.run("Search for solutions to deploying FastAPI apps")
"""
