# state.py
from typing import TypedDict, List, Optional, Literal, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

# --- Intent của người dùng ---
class ScheduleIntent(TypedDict):
    action: Literal["create", "update", "delete", "query", "optimize"]
    urgency: Literal["low", "medium", "high"]
    entities: dict  # Ví dụ: {"time": "10h sáng", "event": "Họp nhóm"}
# --- State Schema của Agent ---
class ScheduleAgentState(TypedDict):
    # Danh sách tin nhắn giữa User và AI
    messages: Annotated[List[BaseMessage], add_messages]

    # Kết quả phân tích yêu cầu user (ScheduleIntent)
    classification: Optional[ScheduleIntent]

    # Dữ liệu lịch hiện tại của người dùng
    calendar_data: Optional[List[dict]]

    # Lịch trình gợi ý từ AI
    proposed_schedule: Optional[dict]

    # Lịch gốc do người dùng yêu cầu (giữ nguyên để làm mốc khi cần gợi ý lại)
    requested_schedule: Optional[dict]

    # Số lần người dùng từ chối bản nháp
    review_attempts: int

    # Người dùng có đồng ý bản nháp lịch không
    is_approved: bool