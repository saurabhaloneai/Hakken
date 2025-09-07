import os
import re
from typing import Dict, Any, Literal
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
                        },
                        "need_user_approve": {
                            "type": "boolean",
                            "description": "Whether to request user approval before performing web search (default: true)",
                            "default": True
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

    def _ensure_dir(self, path: str) -> None:
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass

    def _sanitize(self, s: str) -> str:
        s = s.strip().lower()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        return s.strip("-") or "result"

    def _save_text(self, base_dir: str, base_name: str, suffix: str, content: str) -> str:
        self._ensure_dir(base_dir)
        filename = f"{base_name}-{suffix}.txt"
        path = os.path.join(base_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    async def act(self, 
                 query: str, 
                 max_results: int = 5,
                 topic: Literal["general", "news", "finance"] = "general",
                 include_raw_content: bool = False,
                 need_user_approve: bool = True) -> Dict[str, Any]:
        """
        Perform web search using Tavily API
        
        Args:
            query: Search query string
            max_results: Number of results to return (1-10)
            topic: Search topic category 
            include_raw_content: Whether to include full page content
            need_user_approve: Whether to request user approval (handled by agent)
            
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
            
            # Format the results (save large content to files)
            artifact_dir = os.path.join(os.getcwd(), "artifacts", "web_search")
            max_inline = 800  # keep context small; store long text on disk

            formatted_results = []
            for idx, result in enumerate(search_results.get("results", []), 1):
                title = result.get("title", "") or f"result-{idx}"
                base_name = self._sanitize(title)
                formatted_result = {
                    "title": title,
                    "url": result.get("url", ""),
                    "score": result.get("score", 0)
                }

                content = result.get("content", "") or ""
                raw = result.get("raw_content", "") if include_raw_content and "raw_content" in result else ""

                if content and len(content) > max_inline:
                    path = self._save_text(artifact_dir, base_name, "content", content)
                    formatted_result["content_path"] = path
                    formatted_result["content"] = content[:max_inline] + "…"
                else:
                    formatted_result["content"] = content

                if raw:
                    path = self._save_text(artifact_dir, base_name, "raw", raw)
                    formatted_result["raw_content_path"] = path
                    # do not inline raw content (can be huge); add short preview only
                    preview = raw[:max_inline] if len(raw) > 0 else ""
                    if preview:
                        formatted_result["raw_preview"] = preview + ("…" if len(raw) > max_inline else "")

                formatted_results.append(formatted_result)
            
            return {
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results),
                "topic": topic,
                "status": "success",
                "note": "long content saved to files; use read_file to load content_path/raw_content_path as needed"
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

IMPORTANT: This tool requires user approval before executing web searches to ensure privacy and intentional usage.

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

5. need_user_approve (optional): Request user permission (default: true)
   - Always set to true to respect user privacy
   - Only set to false if user has explicitly granted blanket permission

User Approval Requirements:
- This tool ALWAYS requires user approval before performing web searches
- The user will be prompted to confirm before any search is executed
- User can approve, deny, or modify the search query
- This ensures privacy and prevents unintended external requests

When to Use Web Search:
- User asks "what's new in..." or "latest version of..."
- Discussing deprecated libraries and need current alternatives
- User mentions they're unfamiliar with a topic
- Need current documentation or implementation examples
- Questions about recent events, trends, or developments
- User explicitly requests web search or research

Best Practices:
- Always explain why web search is needed before using this tool
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
