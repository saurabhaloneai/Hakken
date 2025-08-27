"""
Tavily Search Integration for Hakken Research Agent

This module provides web search capabilities using the Tavily API.
It includes both a class-based integration and a simple function interface.
"""

import os
import json
import logging
from typing import Dict, List, Literal, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

try:
    from tavily import TavilyClient
except ImportError:
    raise ImportError(
        "Tavily client not found. Install with: pip install tavily-python"
    )

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Structured search result data"""
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None
    raw_content: Optional[str] = None


class TavilyIntegration:
    """
    Tavily search integration with enhanced functionality for research agents.
    
    Provides web search capabilities with result formatting, content extraction,
    and error handling suitable for AI agent workflows.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Tavily integration.
        
        Args:
            api_key: Tavily API key. If None, will try to get from TAVILY_API_KEY env var
        """
        self.api_key = os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Tavily API key required. Set TAVILY_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        try:
            self.client = TavilyClient(api_key=self.api_key)
            logger.info("Tavily client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Tavily client: {e}")
            raise
    
    def search(
        self,
        query: str,
        max_results: int = 5,
        topic: Literal["general", "news", "finance"] = "general",
        include_raw_content: bool = False,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform web search using Tavily.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (1-20)
            topic: Search topic category
            include_raw_content: Whether to include raw HTML content
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
            
        Returns:
            Dictionary containing search results and metadata
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        
        if not 1 <= max_results <= 20:
            raise ValueError("max_results must be between 1 and 20")
        
        try:
            logger.info(f"Searching for: '{query}' (max_results={max_results}, topic={topic})")
            
            search_params = {
                "query": query.strip(),
                "max_results": max_results,
                "topic": topic,
                "include_raw_content": include_raw_content
            }
            
            if include_domains:
                search_params["include_domains"] = include_domains
            if exclude_domains:
                search_params["exclude_domains"] = exclude_domains
            
            results = self.client.search(**search_params)
            
            logger.info(f"Search completed. Found {len(results.get('results', []))} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise Exception(f"Search operation failed: {str(e)}")
    
    def get_search_context(self, results: Dict[str, Any]) -> str:
        """
        Extract and format search context from results.
        
        Args:
            results: Search results from search() method
            
        Returns:
            Formatted string containing key information from search results
        """
        if not results or "results" not in results:
            return "No search results available."
        
        context_parts = []
        search_results = results["results"]
        
        context_parts.append(f"Found {len(search_results)} search results:")
        context_parts.append("")
        
        for i, result in enumerate(search_results, 1):
            title = result.get("title", "No title")
            url = result.get("url", "No URL")
            content = result.get("content", "No content")
            
            # Truncate content if too long
            if len(content) > 300:
                content = content[:300] + "..."
            
            context_parts.append(f"{i}. **{title}**")
            context_parts.append(f"   URL: {url}")
            context_parts.append(f"   Content: {content}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def extract_urls_from_results(self, results: Dict[str, Any]) -> List[str]:
        """
        Extract all URLs from search results.
        
        Args:
            results: Search results from search() method
            
        Returns:
            List of URLs found in search results
        """
        if not results or "results" not in results:
            return []
        
        urls = []
        for result in results["results"]:
            url = result.get("url")
            if url and url not in urls:
                urls.append(url)
        
        return urls
    
    def extract_content_from_results(self, results: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract structured content from search results.
        
        Args:
            results: Search results from search() method
            
        Returns:
            List of dictionaries containing title, url, content for each result
        """
        if not results or "results" not in results:
            return []
        
        extracted_content = []
        for result in results["results"]:
            content_dict = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0.0),
                "published_date": result.get("published_date", "")
            }
            
            if result.get("raw_content"):
                content_dict["raw_content"] = result["raw_content"]
            
            extracted_content.append(content_dict)
        
        return extracted_content
    
    def extract_key_information(self, results: Dict[str, Any], max_chars: int = 2000) -> List[str]:
        """
        Extract key information from search results with length limit.
        
        Args:
            results: Search results from search() method
            max_chars: Maximum characters per result
            
        Returns:
            List of key information strings from each result
        """
        if not results or "results" not in results:
            return []
        
        key_info = []
        for result in results["results"]:
            content = result.get("content", "")
            if content:
                # Truncate if needed
                if len(content) > max_chars:
                    content = content[:max_chars] + "..."
                key_info.append(content)
        
        return key_info
    
    def format_search_results(self, results: Dict[str, Any], format_type: str = "markdown") -> str:
        """
        Format search results in different formats.
        
        Args:
            results: Search results from search() method
            format_type: Format type ("markdown", "plain", "json")
            
        Returns:
            Formatted string representation of search results
        """
        if not results or "results" not in results:
            return "No search results to format."
        
        if format_type == "json":
            return json.dumps(results, indent=2, ensure_ascii=False)
        
        search_results = results["results"]
        formatted_parts = []
        
        if format_type == "markdown":
            formatted_parts.append(f"# Search Results ({len(search_results)} found)")
            formatted_parts.append("")
            
            for i, result in enumerate(search_results, 1):
                formatted_parts.append(f"## {i}. {result.get('title', 'No title')}")
                formatted_parts.append(f"**URL:** {result.get('url', 'No URL')}")
                formatted_parts.append(f"**Score:** {result.get('score', 0.0)}")
                if result.get("published_date"):
                    formatted_parts.append(f"**Published:** {result['published_date']}")
                formatted_parts.append("")
                formatted_parts.append(result.get("content", "No content"))
                formatted_parts.append("")
                formatted_parts.append("---")
                formatted_parts.append("")
        
        elif format_type == "plain":
            formatted_parts.append(f"SEARCH RESULTS ({len(search_results)} found)")
            formatted_parts.append("=" * 50)
            
            for i, result in enumerate(search_results, 1):
                formatted_parts.append(f"\n{i}. {result.get('title', 'No title')}")
                formatted_parts.append(f"URL: {result.get('url', 'No URL')}")
                formatted_parts.append(f"Score: {result.get('score', 0.0)}")
                if result.get("published_date"):
                    formatted_parts.append(f"Published: {result['published_date']}")
                formatted_parts.append(f"Content: {result.get('content', 'No content')}")
                formatted_parts.append("-" * 30)
        
        return "\n".join(formatted_parts)
    
    def search_and_extract(
        self,
        query: str,
        max_results: int = 5,
        topic: Literal["general", "news", "finance"] = "general"
    ) -> List[SearchResult]:
        """
        Perform search and return structured SearchResult objects.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            topic: Search topic category
            
        Returns:
            List of SearchResult objects
        """
        results = self.search(query, max_results, topic, include_raw_content=True)
        
        search_results = []
        for result in results.get("results", []):
            search_result = SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                score=result.get("score", 0.0),
                published_date=result.get("published_date"),
                raw_content=result.get("raw_content")
            )
            search_results.append(search_result)
        
        return search_results


# Convenience functions for simple usage
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False
) -> Dict[str, Any]:
    """
    Simple function interface for web search.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        topic: Search topic category
        include_raw_content: Whether to include raw HTML content
        
    Returns:
        Dictionary containing search results
    """
    integration = TavilyIntegration()
    return integration.search(query, max_results, topic, include_raw_content)


def search_and_format(
    query: str,
    max_results: int = 5,
    format_type: str = "markdown"
) -> str:
    """
    Search and return formatted results.
    
    Args:
        query: Search query string
        max_results: Maximum number of results
        format_type: Format type ("markdown", "plain", "json")
        
    Returns:
        Formatted search results string
    """
    integration = TavilyIntegration()
    results = integration.search(query, max_results)
    return integration.format_search_results(results, format_type)


def get_search_urls(query: str, max_results: int = 5) -> List[str]:
    """
    Quick function to get just URLs from search.
    
    Args:
        query: Search query string
        max_results: Maximum number of results
        
    Returns:
        List of URLs
    """
    integration = TavilyIntegration()
    results = integration.search(query, max_results)
    return integration.extract_urls_from_results(results)


# Test function for development
def test_search():
    """Test function to verify search functionality"""
    try:
        integration = TavilyIntegration()
        results = integration.search("Python programming", max_results=3)
        print("Search successful!")
        print(f"Found {len(results.get('results', []))} results")
        
        formatted = integration.format_search_results(results, "markdown")
        print("\nFormatted results:")
        print(formatted[:500] + "..." if len(formatted) > 500 else formatted)
        
        return True
    except Exception as e:
        print(f"Search test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test if executed directly
    test_search()