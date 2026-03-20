from typing import Annotated, TypedDict, List, Dict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class SchedulingState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    # 1. Phân loại luồng hội thoại
    intent: str  # Các giá trị: 'greeting', 'off_topic', 'schedule', 'roadmap', 'feedback', 'providing_info'
    missing_info: List[str]  # Danh sách các thông tin user cần cung cấp thêm

    # 2. Tracking thông tin từ các Agents
    user_profile: str  # Kết quả từ Agent 1 (PDF RAG)
    research_data: str  # Kết quả từ Agent 2 (Web Search)
    calendar_slots: str  # Kết quả từ Agent 3 (Calendar Check)

    # 3. Quản lý luồng duyệt nháp
    current_draft: str  # Bản nháp lịch trình / lộ trình Supervisor đưa ra
    is_approved: bool  # Người dùng có đồng ý nháp không?
    user_feedback: str  # Lý do người dùng từ chối (nếu có)