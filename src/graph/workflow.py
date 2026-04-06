from langgraph.graph import StateGraph, END
from src.graph.state import AgentState
from src.graph.nodes import (
    call_supervisor_node,
    call_calendar_node,
    call_research_node,
    # execute_booking_node
)

def build_schedule_assistant_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", call_supervisor_node)
    workflow.add_node("calendar_expert", call_calendar_node)
    workflow.add_node("researcher", call_research_node)
    # workflow.add_node("booker", execute_booking_node)
    workflow.set_entry_point("supervisor")

    def router_logic(state):
        target = state.get("next")
        if target == "CalendarAgent": return "go_to_calendar"
        if target == "ResearchAgent": return "go_to_research"
        return "finish"


    workflow.add_conditional_edges(
        "supervisor",
        router_logic,
        {
            "go_to_calendar": "calendar_expert",
            "go_to_research": "researcher",
            "finish": END
        }
    )

    workflow.add_edge("calendar_expert", "supervisor")
    workflow.add_edge("researcher", "supervisor")

    return workflow.compile()