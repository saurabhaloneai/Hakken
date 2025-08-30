"""
Single deep research task using the modularized DeepAgent system with Tavily search.
"""

import os
from hakken import create_deep_agent, SubAgentConfig
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Custom Tavily search tool
def tavily_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily AI-powered search."""
    try:
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=True
        )
        
        # Format results
        formatted_results = []
        
        # Add the AI-generated answer if available
        if response.get('answer'):
            formatted_results.append(f"AI Summary: {response['answer']}\n")
        
        # Add individual search results
        for i, result in enumerate(response.get('results', []), 1):
            formatted_results.append(f"{i}. {result['title']}")
            formatted_results.append(f"   URL: {result['url']}")
            formatted_results.append(f"   Content: {result['content'][:300]}...")
            formatted_results.append("")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Search failed: {str(e)}"

def web_scrape(url: str) -> str:
    """Extract content from a specific URL using Tavily."""
    try:
        response = tavily_client.extract(urls=[url])
        if response and response.get('results'):
            result = response['results'][0]
            return f"Title: {result.get('title', 'N/A')}\nContent: {result.get('raw_content', 'No content extracted')}"
        return "No content extracted"
    except Exception as e:
        return f"Extraction failed: {str(e)}"

# Sub-agent configurations
research_agent = SubAgentConfig(
    name="research-agent",
    description="Specialized in web research and data gathering using AI-powered search",
    prompt="""You are a research specialist with access to advanced web search capabilities. 
    Use tavily_search for comprehensive research and web_scrape for detailed content extraction.
    Focus on gathering comprehensive, accurate, and up-to-date information.""",
    tools=["tavily_search", "web_scrape", "write_file", "read_file"]
)

analysis_agent = SubAgentConfig(
    name="analysis-agent", 
    description="Specialized in data analysis and processing",
    prompt="""You are an analysis expert. Process research data, identify patterns, 
    compare information from multiple sources, and draw meaningful insights.
    Focus on critical thinking and thorough analysis.""",
    tools=["read_file", "write_file", "tavily_search"]
)

report_agent = SubAgentConfig(
    name="report-agent",
    description="Specialized in report writing and synthesis", 
    prompt="""You are a report writing specialist. Create comprehensive, well-structured reports
    that synthesize research and analysis into clear, actionable insights.
    Focus on clarity, organization, and professional presentation.""",
    tools=["read_file", "write_file", "save_to_disk"]
)

# Create the deep research agent
agent = create_deep_agent(
    tools=[tavily_search, web_scrape],
    instructions="""You are a comprehensive research and analysis agent with access to 
    advanced web search capabilities. Use your planning system to break down complex tasks,
    delegate to specialized sub-agents, and create thorough, well-researched outputs.""",
    subagents=[research_agent, analysis_agent, report_agent],
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-sonnet-4-20250514"
)

def deep_research(research_topic: str):
    """Perform single comprehensive deep research on any topic."""
    input_data = {
        "messages": [
            {
                "role": "user", 
                "content": f"""Research and analyze {research_topic}. 
                Conduct thorough research, analyze the data, and create a comprehensive report 
                with key findings, trends, and actionable insights."""
            }
        ],
        "files": {}
    }
    
    result = agent.invoke(input_data)
    return result

if __name__ == "__main__":
    print("=== Single Deep Research with DeepAgent ===\n")
    
    # Check API keys
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Please set ANTHROPIC_API_KEY environment variable")
        exit(1)
    
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️  Please set TAVILY_API_KEY environment variable")
        exit(1)
    
    # Define your research topic here
    RESEARCH_TOPIC = "the current state of renewable energy technology, focusing on solar, wind, and battery storage costs, efficiency trends, and market adoption"
    
    print(f"🔍 Starting deep research on: {RESEARCH_TOPIC}")
    result = deep_research(RESEARCH_TOPIC)
    
    print("\n📁 Generated files:")
    for filename in result["files"].keys():
        size = len(result["files"][filename])
        print(f"  - {filename} ({size:,} chars)")
    
    print(f"\n💬 Total messages: {len(result['messages'])}")
    print(f"🏁 Final result: {result['messages'][-1]['content'][:200]}...")
    
    # Save the main report
    if "final_output.md" in result["files"]:
        os.makedirs("output", exist_ok=True)
        with open("output/research_report.md", "w") as f:
            f.write(result["files"]["final_output.md"])
        print("\n💾 Report saved to output/research_report.md")
    
    print("\n✅ Deep research completed!")