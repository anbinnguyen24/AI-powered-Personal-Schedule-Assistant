from typing import Literal
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from langgraph.graph import MessagesState, StateGraph, START, END


@tool
def check_calendar(time: str):
    """Check if the time slot is busy."""
    return "Busy" if "14:00" in time else "Available"


def assistant(state: MessagesState):
    last_msg = state["messages"][-1]

    # First turn: User asks for 14:00
    if isinstance(last_msg, HumanMessage):
        return {"messages": [
            AIMessage(content="", tool_calls=[{"name": "check_calendar", "args": {"time": "14:00"}, "id": "1"}])]}

    # Second turn: Tool returned "Busy"
    if isinstance(last_msg, ToolMessage) and last_msg.content == "Busy":
        return {"messages": [AIMessage(content="14:00 is busy. How about 15:00?")]}


def tool_node(state: MessagesState):
    tool_call = state["messages"][-1].tool_calls[0]
    result = check_calendar.invoke(tool_call["args"])
    return {"messages": [ToolMessage(content=str(result), tool_call_id=tool_call["id"])]}


def router(state: MessagesState) -> Literal["tool_node", "__end__"]:
    return "tool_node" if state["messages"][-1].tool_calls else END


# Build Graph
workflow = StateGraph(MessagesState)
workflow.add_node("assistant", assistant)
workflow.add_node("tool_node", tool_node)
workflow.add_edge(START, "assistant")
workflow.add_conditional_edges("assistant", router)
workflow.add_edge("tool_node", "assistant")

app = workflow.compile()

# Run
for m in app.invoke({"messages": [HumanMessage(content="Meet at 14:00")]})["messages"]:
    m.pretty_print()