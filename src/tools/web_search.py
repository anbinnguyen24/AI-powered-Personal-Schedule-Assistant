from tavily import TavilyClient
from langchain.tools import tool

tavily = TavilyClient(api_key="your_key")

@tool
def research_topic(query: str) -> str:
    """Research topic/event on internet."""
    results = tavily.search(query)
    return f"Research '{query}': {results}"