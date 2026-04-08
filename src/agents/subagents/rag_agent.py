from src.prompts.rag_agent import RAG_AGENT_PROMPT
from src.tools.rag_tool import search_knowledge_base

rag_subagent = {
    "name": "rag-agent",
    "description": (
        "Tìm kiếm thông tin từ tài liệu PDF và cơ sở tri thức nội bộ. "
        "Dùng agent này khi cần tra cứu quy chế, nội quy, hoặc tài liệu tham khảo."
    ),
    "system_prompt": RAG_AGENT_PROMPT,
    "tools": [search_knowledge_base],
}
