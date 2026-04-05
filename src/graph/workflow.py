from langgraph.graph import StateGraph, END
from src.graph.state import AssistantState
from src.graph.nodes import (
    call_supervisor_node, 
    call_calendar_node, 
    call_research_node, 
    execute_booking_node
)

def build_schedule_assistant_graph():
    # 1. Khởi tạo đồ thị với cấu trúc dữ liệu (State) đã định nghĩa
    workflow = StateGraph(AssistantState)

    # 2. Đăng ký các Node (Trạm xử lý) vào đồ thị
    # Tên node viết trong "" sẽ dùng để gọi ở bước nối đường (Edge)
    workflow.add_node("supervisor", call_supervisor_node)
    workflow.add_node("calendar_expert", call_calendar_node)
    workflow.add_node("researcher", call_research_node)
    workflow.add_node("booker", execute_booking_node)

    # 3. Thiết lập ĐIỂM BẮT ĐẦU
    # Mọi yêu cầu từ người dùng đều phải qua "Ông tổ trưởng" Supervisor trước
    workflow.set_entry_point("supervisor")

    # 4. Thiết lập CÁC ĐƯỜNG ĐI CÓ ĐIỀU KIỆN (Conditional Edges)
    # Supervisor sẽ nhìn vào state["next_worker"] để quyết định rẽ nhánh
    def router_logic(state: AssistantState):
        target = state.get("next_worker")
        if target == "calendar_agent":
            return "go_to_calendar"
        elif target == "research_agent":
            return "go_to_research"
        elif target == "execute_booking":
            return "go_to_booking"
        else:
            return "finish"

    workflow.add_conditional_edges(
        "supervisor",                  # Điểm xuất phát của nhánh
        router_logic,                  # Hàm logic quyết định hướng đi
        {
            "go_to_calendar": "calendar_expert",
            "go_to_research": "researcher",
            "go_to_booking": "booker",
            "finish": END              # Kết thúc luồng, trả kết quả cho user
        }
    )

    # 5. Thiết lập CÁC ĐƯỜNG ĐI CỐ ĐỊNH (Normal Edges)
    # Sau khi các chuyên gia làm xong, họ PHẢI quay lại báo cáo cho Supervisor
    workflow.add_edge("calendar_expert", "supervisor")
    workflow.add_edge("researcher", "supervisor")
    
    # Sau khi chốt lịch xong thì kết thúc luôn
    workflow.add_edge("booker", END)

    # 6. BIÊN DỊCH (Compile)
    # Chuyển sơ đồ thiết kế thành một ứng dụng có thể chạy được
    app = workflow.compile()
    
    return app