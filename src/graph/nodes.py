from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode, tools_condition
from src.tools.google_calendar import check_user_availability, create_event
from src.tools.user_db import get_user_info
from src.tools.web_search import research_topic
from src.graph.state import SchedulingState

model = ChatOpenAI(model="gpt-4o-mini")

# Supervisor Node
async def supervisor_node(state: SchedulingState):
    """Supervisor quyết định next stage."""
    stage = state.get("current_stage", "research")

    if stage == "research":
        return {"next": "research_agent", "current_stage": "research"}
    elif stage == "research" and state.get("research_data"):
        return {"next": "calendar_agent", "current_stage": "calendar"}
    elif state.get("available_slots"):
        return {"next": "proposal_agent", "current_stage": "proposal"}
    elif state.get("human_approved"):
        return {"next": "create_event", "current_stage": "scheduled"}
    else:
        return {"next": "supervisor", "current_stage": stage}


# Research Agent Node
async def research_agent_node(state):
    research_model = model.bind_tools([get_user_info, research_topic])
    # Execute research logic
    return {"research_data": {...}, "messages": [...]}


# Calendar Agent Node
async def calendar_agent_node(state):
    calendar_model = model.bind_tools([check_user_availability])
    # Execute calendar check
    return {"available_slots": [...], "messages": [...]}


# Proposal Agent (Human-in-loop)
async def proposal_agent_node(state):
    """Đề xuất schedule và chờ human approve."""
    proposal = {
        "time": state["available_slots"][0],
        "reason": "Best fit for user's morning preference"
    }
    return {"proposal": proposal, "messages": [...], "human_approved": False}