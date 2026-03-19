from typing import Annotated, TypedDict, List, Dict
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage

class SchedulingState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    user_info: Dict  # {"name", "timezone", "prefs"}
    research_data: Dict
    available_slots: List[Dict]  # [{"time": "10AM", "duration": 60}]
    proposal: Dict  # Proposed schedule
    human_approved: bool
    current_stage: str  # "research" | "calendar" | "proposal" | "approved"