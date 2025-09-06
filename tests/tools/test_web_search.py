"""Tests for WebSearch tool"""
import pytest
import os
from unittest.mock import Mock, patch
from src.tools.web_search import WebSearch


class TestWebSearch:
    
    @pytest.fixture
    def web_search(self):
        return WebSearch()
    
    def test_tool_name(self, web_search):
        assert web_search.get_tool_name() == "web_search"
    
    def test_json_schema(self, web_search):
        schema = web_search.json_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "web_search"
        
       
        params = schema["function"]["parameters"]["properties"]
        assert "query" in params
        assert "max_results" in params
        assert "need_user_approve" in params
        assert params["query"]["type"] == "string"
        assert params["topic"]["enum"] == ["general", "news", "finance"]
        assert params["need_user_approve"]["type"] == "boolean"
        
        assert schema["function"]["parameters"]["required"] == ["query"]
    
    def test_status_without_dependencies(self, web_search):
        """Test status when dependencies are not available"""
        status = web_search.get_status()

        assert "not" in status.lower()
    
    @pytest.mark.asyncio
    async def test_act_without_tavily(self, web_search):
        """Test behavior when tavily is not available"""
        result = await web_search.act("test query")
        
        assert result["status"] == "failed"
        assert "error" in result
        assert any(term in result["error"] for term in ["tavily", "package", "api key"])
    
    @pytest.mark.asyncio
    async def test_parameter_validation_with_mock(self, web_search):
        """Test parameter validation with mocked client"""
        mock_client = Mock()
        mock_client.search.return_value = {"results": []}
 
        web_search.client = mock_client
 
        await web_search.act("test", max_results=15, need_user_approve=False)
        call_args = mock_client.search.call_args
        assert call_args.kwargs["max_results"] == 10  
        
        # Test min clamping
        await web_search.act("test", max_results=0, need_user_approve=False)
        call_args = mock_client.search.call_args
        assert call_args.kwargs["max_results"] == 1


class TestWebSearchWithMockedClient:

    @pytest.fixture
    def web_search_with_mock(self):

        mock_client = Mock()
        mock_client.search.return_value = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.9
                }
            ]
        }
        
        web_search = WebSearch()
        web_search.client = mock_client
        return web_search, mock_client
    
    @pytest.mark.asyncio
    async def test_successful_search(self, web_search_with_mock):
 
        web_search, mock_client = web_search_with_mock
        
        result = await web_search.act("Python tutorial", need_user_approve=False)
        
        assert result["status"] == "success"
        assert result["query"] == "Python tutorial"
        assert result["total_results"] == 1
        assert len(result["results"]) == 1
 
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args
        assert call_args.kwargs["query"] == "Python tutorial"
    
    @pytest.mark.asyncio
    async def test_search_with_options(self, web_search_with_mock):
        web_search, mock_client = web_search_with_mock
        
        await web_search.act(
            query="news", 
            max_results=5,
            topic="news",
            include_raw_content=True,
            need_user_approve=False
        )

        call_args = mock_client.search.call_args
        assert call_args.kwargs["query"] == "news"
        assert call_args.kwargs["max_results"] == 5
        assert call_args.kwargs["topic"] == "news"
        assert call_args.kwargs["include_raw_content"] is True
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, web_search_with_mock):
   
        web_search, mock_client = web_search_with_mock
        mock_client.search.side_effect = Exception("API Error")
        
        result = await web_search.act("test", need_user_approve=False)
        
        assert result["status"] == "failed"
        assert "web search failed" in result["error"]
        assert "API Error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_empty_results(self, web_search_with_mock):
       
        web_search, mock_client = web_search_with_mock
        mock_client.search.return_value = {"results": []}
        
        result = await web_search.act("rare query", need_user_approve=False)
        
        assert result["status"] == "success"
        assert result["total_results"] == 0
        assert len(result["results"]) == 0
