from langgraph.graph import StateGraph, START, END
from src.graph.state import SchedulingState
from src.graph.nodes import supervisor_node,research_agent_node,calendar_agent_node,proposal_agent_node
from src.tools.google_calendar import create_event,check_user_availability
from langgraph.prebuilt import ToolNode, tools_condition


def create_workflow():
    workflow = StateGraph(SchedulingState)

    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research_agent", research_agent_node)
    workflow.add_node("calendar_agent", calendar_agent_node)
    workflow.add_node("proposal_agent", proposal_agent_node)

    # Add tool nodes
    tool_node = ToolNode([check_user_availability, create_event])
    workflow.add_node("tools", tool_node)

    # Routing edges
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {
            "research_agent": "research_agent",
            "calendar_agent": "calendar_agent",
            "proposal_agent": "proposal_agent",
            "tools": "tools",
            END: END
        }
    )

    # Agent → tools → back to agent
    workflow.add_conditional_edges(
        "research_agent", tools_condition, {"tools": "tools", END: END}
    )

    workflow.set_entry_point("supervisor")

    return workflow.compile()