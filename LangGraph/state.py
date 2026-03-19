from typing import TypedDict, Annotated, List, Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt, RetryPolicy
from langchain_core.messages import BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
import json
from langchain_ollama import ChatOllama
load_dotenv()

llm = ChatOllama(model="llama3.1")

class ScheduleIntent(TypedDict):
    action: Literal["create", "update", "delete", "query", "optimize"]
    urgency: Literal["low", "medium", "high"]
    entities: dict

class ScheduleAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    classification: Optional[ScheduleIntent]
    calendar_data: Optional[List[dict]]
    proposed_schedule: Optional[dict]
    is_approved: bool

# ---BUILD NODES---
def analyze_request(state: ScheduleAgentState):
    structured_llm = llm.with_structured_output(ScheduleIntent)
    user_msg = state["messages"][-1].content
    result = structured_llm.invoke(f"Phân tích yêu cầu sau để quản lý lịch trình: {user_msg}")

    return Command(update={"Đang xử lí yêu cầu": result}, goto="calendar_check")


def calendar_check(state: ScheduleAgentState):
    #giả định
    raw_data = [
        {"event": "Họp nhóm đồ án", "time": "09:00", "date": "2026-03-20"},
        {"event": "Đi tập Gym", "time": "17:00", "date": "2026-03-20"}
    ]
    return Command(update={"calendar_data": raw_data}, goto="schedule_advisor")

def schedule_advisor(state: ScheduleAgentState):
    intent = state["classification"]
    calendar = state["calendar_data"]

    prompt = f"""
        Người dùng muốn: {intent['action']} cho việc {intent['entities']}.
        Lịch hiện tại của họ: {calendar}.
        Hãy đưa ra một đề xuất lịch trình hợp lý nhất và giải quyết các xung đột nếu có.
        """
    # LLM đưa ra câu trả lời
    response = llm.invoke(prompt)
    return Command(update={"proposed_schedule": {"content": response.content}}, goto="human_review")

def human_review(state: ScheduleAgentState):
    draft = state.get("proposed_schedule", {})
    decision = interrupt({
        "info": "Tôi đã lập xong bản nháp lịch trình. Bạn có đồng ý cập nhật không?",
        "proposed_schedule": draft
    })

    if decision.get("approved") is True:
        return Command(
            update={"is_approved": True},
            goto="update_save_response"
        )
    return Command(update={"is_approved": False}, goto=END)

def update_save_response(state: ScheduleAgentState):
    event_to_save = state["proposed_schedule"]
    print(f"--- Đang thực hiện ghi vào Google Calendar: {event_to_save} ---")
    return {
        "messages": [
            AIMessage(
                content=f"Xong! tôi đã cập nhật lịch trình '{event_to_save.get('content')}' vào Google Calendar rồi ạ.")
        ]
    }

# ---KẾT NỐI ĐỒ THỊ ---
# 1. Khởi tạo đồ thị với State Schema
workflow = StateGraph(ScheduleAgentState)
# 2. Thêm các Node và cấu trúc xử lý lỗi (Retry Policy)
workflow.add_node("analyze_request", analyze_request)

# Áp dụng Retry cho các node gọi API bên ngoài (Transient Errors)
workflow.add_node(
    "calendar_check",
    calendar_check,
    retry_policy=RetryPolicy(max_attempts=3)
)

workflow.add_node("schedule_advisor", schedule_advisor)
workflow.add_node("human_review", human_review)
workflow.add_node("update_save_response", update_save_response)

# 3. Thiết lập các cạnh (Edges) cố định
workflow.add_edge(START, "analyze_request")
workflow.add_edge("update_save_response", END)

# 4. Biên dịch đồ thị (Compile)
# Bắt buộc có checkpointer để dùng được interrupt() và lưu trạng thái (Persistence)
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


def run_demo():
    # 1. Khởi tạo trạng thái ban đầu
    # Giả sử Agent đã chạy qua các bước trước và đã có bản nháp (proposed_schedule)
    initial_input = {
        "messages": [("user", "Sắp xếp lịch họp nhóm vào 10h sáng mai")],
        "proposed_schedule": {"content": "Họp nhóm đồ án tại Cafe AI, lúc 10:00 - 11:00 ngày 20/03/2026"},
        "is_approved": False
    }

    # Cấu hình thread_id để MemorySaver có thể lưu lại trạng thái
    config = {"configurable": {"thread_id": "demo_001"}}

    print("\n=== AGENT BẮT ĐẦU CHẠY ===")

    # 2. Chạy Agent lần đầu
    # Nó sẽ chạy Analyze -> Calendar -> Advisor và DỪNG LẠI ở human_review
    for event in app.stream(initial_input, config, stream_mode="values"):
        # In ra để xem Agent đang ở đâu (tùy chọn)
        pass

    # 3. Kiểm tra xem Agent có đang đợi xác nhận không
    state = app.get_state(config)

    if state.next and state.next[0] == "human_review":
        print("\n--- THÔNG BÁO TỪ AGENT ---")
        print(f"Bản nháp đề xuất: {state.values['proposed_schedule']['content']}")

        # Lấy tương tác từ Terminal
        user_choice = input("\nBạn có đồng ý với lịch trình này không? (y/n): ").strip().lower()
        if user_choice == 'y':
            print("\n=> Đang gửi lệnh ĐỒNG Ý tới Agent...")
            app.invoke(Command(resume={"approved": True}), config)
        else:
            print("\n=> Đang gửi lệnh TỪ CHỐI tới Agent...")
            app.invoke(Command(resume={"approved": False}), config)

    # 4. Lấy kết quả cuối cùng sau khi đã Resume
    final_state = app.get_state(config)
    if "messages" in final_state.values:
        print("\n=== PHẢN HỒI CUỐI CÙNG ===")
        print(final_state.values["messages"][-1].content)

# Chạy demo
if __name__ == "__main__":
    run_demo()
