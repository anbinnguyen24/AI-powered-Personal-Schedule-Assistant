from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from src.graph.state import SchedulingState
from src.graph.nodes import (
    supervisor_node,
    research_agent_node,
    calendar_agent_node,
    proposal_agent_node
)
from src.tools import google_calendar,user_db,web_search


def create_scheduling_workflow() -> Any:
    """Tạo full LangGraph workflow."""

    # Khởi tạo graph với custom state
    workflow = StateGraph(SchedulingState)

    # 1. Add custom agent nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research", research_agent_node)
    workflow.add_node("calendar", calendar_agent_node)
    workflow.add_node("proposal", proposal_agent_node)

    # 2. Add ToolNode - QUAN TRỌNG!
    tool_node = ToolNode(google_calendar,user_db,web_search)  # Auto execute tools
    workflow.add_node("tools", tool_node)

    # 3. Edges: Luồng từ START → supervisor
    workflow.add_edge(START, "supervisor")

    # 4. Supervisor routing → agents/tools
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next_stage", "research"),
        {
            "research": "research",
            "calendar": "calendar",
            "proposal": "proposal",
            "END": END
        }
    )

    # 5. Agent → ToolNode → back to agent (ReAct loop)
    workflow.add_conditional_edges(
        "research",
        tools_condition,  # Magic: check if LLM gọi tool
        {"tools": "tools", END: END}
    )
    workflow.add_conditional_edges(
        "calendar",
        tools_condition,
        {"tools": "tools", END: END}
    )
    workflow.add_conditional_edges(
        "proposal",
        tools_condition,
        {"tools": "tools", END: END}
    )

    # 6. ToolNode luôn quay về supervisor
    workflow.add_edge("tools", "supervisor")

    # Compile với checkpointer (persistence)
    app = workflow.compile(checkpointer="memory")  # Hoặc Postgres

    return app