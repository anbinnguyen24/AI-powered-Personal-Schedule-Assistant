from typing import Annotated, TypedDict
import operator
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    messages: Annotated[list, operator.add]
    is_confirmed: bool


def assistant(state: State):
    print("--- Đang phân tích yêu cầu ---")
    if "họp" in state["messages"][-1]:
        return {"next_step": "book_meeting"}
    return {"next_step": "just_chat"}

def booking_node(state: State):
    print("--- Đang thực hiện đặt lịch ---")
    return {"messages": ["Bot: Tôi đã đặt lịch họp cho bạn."]}

# 2. Định nghĩa hàm điều hướng (Router) cho Conditional Edge
def route_next(state: State):
    if state["next_step"] == "book_meeting":
        return "booking"
    return END

# 3. Xây dựng sơ đồ (Graph)
workflow = StateGraph(State)
workflow.add_node("assistant", assistant)
workflow.add_node("booking", booking_node)

# Thiết lập đường đi
workflow.add_edge(START, "assistant")
workflow.add_conditional_edges(
    "assistant",
    route_next,
    {"booking": "booking", END: END}
)
workflow.add_edge("booking", END)
app = workflow.compile()