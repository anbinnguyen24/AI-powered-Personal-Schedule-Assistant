from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class OuterAgentState(TypedDict):
    """Trạng thái lưu trữ tin nhắn cho vòng lặp ngoài cùng của LangGraph."""
    messages: Annotated[list, add_messages]