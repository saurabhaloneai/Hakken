import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))

def internet_search(query, max_results=5, topic="general", include_raw_content=False):
    return tavily_client.search(query, max_results=max_results, include_raw_content=include_raw_content, topic=topic)

