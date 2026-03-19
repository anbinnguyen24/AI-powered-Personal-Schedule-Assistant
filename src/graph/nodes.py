from src.tools.google_calendar import calendar_tools
from src.tools.user_db import get_user_info
from src.tools.web_search import research_topic
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
import os

def create_scheduling_workflow():
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise ValueError("Chưa tìm thấy HF_TOKEN trong file .env!")
    model = ChatOpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key= hf_token,
        model="Qwen/Qwen2.5-72B-Instruct",
        temperature=0
    )

    all_tools = calendar_tools + [get_user_info, research_topic]

    system_prompt = """Bạn là trợ lý ảo quản lý lịch trình cá nhân cực kỳ thông minh.

    QUY TẮC LÀM VIỆC:
    1. TÔN TRỌNG NGƯỜI DÙNG: Nếu người dùng yêu cầu giờ giấc cụ thể (VD: 9h sáng, 2h chiều), BẮT BUỘC phải lấy đúng giờ đó để tra cứu và đặt lịch. Không tự ý đổi giờ của họ.
    2. SỬ DỤNG TOOL: Dùng công cụ Google Calendar để kiểm tra xem giờ đó có bị trùng lịch không. 
    3. ĐỀ XUẤT: Sau khi kiểm tra, tổng hợp lại bằng tiếng Việt (Thời gian, địa điểm, sự kiện) và hỏi: "Bạn có đồng ý để tôi tạo lịch này trên Google Calendar không?".
    4. TẠO LỊCH: Chỉ dùng tool tạo sự kiện khi người dùng gõ "Đồng ý", "OK", "Tạo đi".
    """

    app = create_react_agent(
        model,
        tools=all_tools,
        state_modifier=system_prompt,
        checkpointer=MemorySaver()
    )

    return app