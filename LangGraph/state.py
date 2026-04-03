from typing import Annotated, TypedDict
import operator
from langgraph.graph import StateGraph, START, END

# BƯỚC 1: ĐỊNH NGHĨA STATE
class AgentState(TypedDict):
    # Dùng operator.add để tin nhắn mới được 'nối' thêm vào list cũ (Reducer)
    messages: Annotated[list, operator.add]
    # Trường này không có Annotated nên sẽ bị ghi đè (Override)
    is_confirmed: bool

# BƯỚC 2: ĐỊNH NGHĨA NODE
def scheduling_node(state: AgentState):
    # Giả lập logic: Agent nhận diện yêu cầu và phản hồi
    print("--- Agent đang xử lý lịch trình ---")
    return {
        "messages": ["Bot: Tôi đã ghi nhận lịch hẹn lúc 2h chiều của bạn."],
        "is_confirmed": True
    }

# --- BƯỚC 3: XÂY DỰNG GRAPH ---
workflow = StateGraph(AgentState)
workflow.add_node("scheduler", scheduling_node)
workflow.add_edge(START, "scheduler")
workflow.add_edge("scheduler", END)

# Biên dịch thành ứng dụng
app = workflow.compile()

# BƯỚC 4: CHẠY VÀ XEM KẾT QUẢ
initial_input = {
    "messages": ["User: Đặt lịch họp giúp tôi"],
    "is_confirmed": False
}
final_state = app.invoke(initial_input)

print("\nKẾT QUẢ CUỐI CÙNG TRONG STATE:")
print(final_state)