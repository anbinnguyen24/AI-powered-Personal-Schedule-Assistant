import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools import get_current_schedule, add_event_to_calendar, analyze_free_time
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
memory = MemorySaver()
load_dotenv()

# --- CẤU HÌNH MODEL-------------------
llm = ChatOpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ.get("HF_TOKEN"),
    model="Qwen/Qwen2.5-72B-Instruct",
    temperature=0.1
)

# --- BƯỚC 1: Tạo các Subagents chuyên biệt ---
calendar_subagent = create_react_agent(
    llm,
    tools=[get_current_schedule, add_event_to_calendar]
)

analysis_subagent = create_react_agent(
    llm,
    tools=[analyze_free_time]
)

@tool
def calendar_manager(query: str):
    """Dùng để tra cứu hoặc thêm lịch trình cá nhân."""
    response = calendar_subagent.invoke({"messages": [("human", query)]})
    return response["messages"][-1].content

@tool
def schedule_advisor(query: str):
    """Dùng để xin lời khuyên, tìm khung giờ trống hoặc tối ưu lịch làm việc."""
    response = analysis_subagent.invoke({"messages": [("human", query)]})
    return response["messages"][-1].content

# --- BƯỚC 3: Tạo Main Agent (Supervisor) ---
main_agent = create_react_agent(
    llm,
    tools=[calendar_manager, schedule_advisor],
    prompt="Bạn là Trợ lý Lập lịch thông minh. Quy trình: "
           "1. Kiểm tra lịch hiện tại qua calendar_manager. "
           "2. Nhờ tư vấn qua schedule_advisor. "
           "3. Đưa ra câu trả lời cuối cùng cho người dùng."
            "Nếu đã có đủ thông tin từ công cụ, hãy trả lời trực tiếp cho người dùng và kết thúc, không được lặp lại quy trình",
    checkpointer=memory
)