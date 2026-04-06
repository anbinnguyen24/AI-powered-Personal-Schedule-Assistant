from langgraph.prebuilt import create_react_agent
from src.tools.rag_tool import consult_guidelines
from src.tools.web_search import web_search_tool

def get_research_agent(llm):
    tools = [consult_guidelines, web_search_tool]
    system_message = (
        "Bạn là trợ lý nghiên cứu. Hãy ưu tiên tìm thông tin trong tài liệu nội bộ bằng 'consult_guidelines'. "
        "Nếu không thấy, hãy sử dụng tìm kiếm web để bổ sung thông tin."
    )
    return create_react_agent(llm, tools, state_modifier=system_message)