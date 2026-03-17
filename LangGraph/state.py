from typing import TypedDict, Optional, List, Literal

# Định nghĩa cấu trúc cho kết quả phân tích yêu cầu
class ScheduleClassification(TypedDict):
    intent: Literal["create", "update", "delete", "query"]
    urgency: Literal["low", "medium", "high"]
    entities: dict

class ScheduleAgentState(TypedDict):
    # Raw data input
    user_request: str
    user_id: str

    # Classification result (Dùng cho điều hướng - Routing)
    classification: Optional[ScheduleClassification]

    # Raw search/API results
    calendar_data: Optional[List[dict]]
    personal_preferences: Optional[List[str]] # Kết quả từ RAG

    # Create contene
    proposed_schedule: Optional[dict]
    messages: List[str]
