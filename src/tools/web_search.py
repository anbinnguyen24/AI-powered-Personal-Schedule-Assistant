from langchain_community.tools import DuckDuckGoSearchResults
from ddgs import DDGS
web_search_tool = DuckDuckGoSearchResults(
    max_results=5,
    description="Tìm kiếm thông tin, tin tức, sự kiện trên Internet."
)