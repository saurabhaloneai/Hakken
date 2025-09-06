import os
from typing import Dict, Any, Literal, Optional
from .tool_interface import ToolInterface

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


class WebSearch(ToolInterface):
    """Web search tool using Tavily API for real-time information"""
    
    def __init__(self):
        super().__init__()
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Tavily client if API key is available"""
        if not TAVILY_AVAILABLE:
            return
        
        api_key = os.environ.get("TAVILY_API_KEY")
        if api_key:
            try:
                self.client = TavilyClient(api_key=api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize Tavily client: {e}")
    
    @staticmethod
    def get_tool_name() -> str:
        return "web_search"

    def json_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": self._tool_description(),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to find information on the web"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of search results to return (default: 5)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 10
                        },
                        "topic": {
                            "type": "string",
                            "enum": ["general", "news", "finance"],
                            "description": "Topic category for focused search (default: general)",
                            "default": "general"
                        },
                        "include_raw_content": {
                            "type": "boolean",
                            "description": "Whether to include raw content from web pages (default: false)",
                            "default": False
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def get_status(self) -> str:
        if not TAVILY_AVAILABLE:
            return "tavily package not installed - web search unavailable"
        if not self.client:
            return "tavily api key not configured - web search unavailable"
        return "ready - web search available"

    async def act(self, 
                 query: str, 
                 max_results: int = 5,
                 topic: Literal["general", "news", "finance"] = "general",
                 include_raw_content: bool = False) -> Dict[str, Any]:
        """
        Perform web search using Tavily API
        
        Args:
            query: Search query string
            max_results: Number of results to return (1-10)
            topic: Search topic category 
            include_raw_content: Whether to include full page content
            
        Returns:
            Dictionary containing search results and metadata
        """
        if not TAVILY_AVAILABLE:
            return {
                "error": "tavily package not installed. install with: pip install tavily-python",
                "status": "failed"
            }
        
        if not self.client:
            return {
                "error": "tavily api key not configured. set TAVILY_API_KEY environment variable",
                "status": "failed"
            }
        
        try:
            # Validate parameters
            max_results = max(1, min(10, max_results))
            
            # Perform the search
            search_results = self.client.search(
                query=query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic
            )
            
            # Format the results
            formatted_results = []
            for result in search_results.get("results", []):
                formatted_result = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0)
                }
                
                if include_raw_content and "raw_content" in result:
                    formatted_result["raw_content"] = result["raw_content"]
                
                formatted_results.append(formatted_result)
            
            return {
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results),
                "topic": topic,
                "status": "success"
            }
            
        except Exception as e:
            return {
                "error": f"web search failed: {str(e)}",
                "query": query,
                "status": "failed"
            }
    
    def _tool_description(self) -> str:
        return """
Search the web for real-time information using Tavily API for research and fact-checking.

This tool provides access to current web information and is particularly useful when:
- User asks about recent events, news, or current information
- Discussing new technologies, frameworks, or libraries
- Looking up documentation for unfamiliar or deprecated technologies
- Researching best practices or current implementations
- User explicitly requests web search or mentions needing up-to-date information
- Dealing with topics that may have changed since your training data

Search Parameters:
1. query (required): The search terms to look up
   - Be specific and use relevant keywords
   - Include version numbers, dates, or context when relevant
   - Examples: "React 18 new features", "Python async best practices 2024"

2. max_results (optional): Number of results to return (1-10, default: 5)
   - Use smaller numbers for focused searches
   - Use larger numbers for comprehensive research

3. topic (optional): Search category for better results
   - "general": Default for most searches
   - "news": For current events and recent developments  
   - "finance": For financial markets and economic information

4. include_raw_content (optional): Include full page content (default: false)
   - Set to true when you need detailed information from sources
   - Use sparingly as it significantly increases response size

When to Use Web Search:
- User asks "what's new in..." or "latest version of..."
- Discussing deprecated libraries and need current alternatives
- User mentions they're unfamiliar with a topic
- Need current documentation or implementation examples
- Questions about recent events, trends, or developments
- User explicitly requests web search or research

Best Practices:
- Use specific, targeted queries for better results
- Start with general topic, then narrow down if needed
- Check result scores to identify most relevant sources
- Combine web search with code analysis for comprehensive answers
- Always cite sources when using web search information

Output Format:
- Returns array of search results with title, URL, content snippet, and relevance score
- Includes search metadata (query, topic, result count)
- Error handling for API issues or configuration problems

Example Use Cases:
- "What are the new features in React 18?" → web_search("React 18 new features")
- "How to migrate from deprecated package X?" → web_search("alternative to [package] 2024")
- "Latest best practices for async Python?" → web_search("Python async best practices 2024")
"""
