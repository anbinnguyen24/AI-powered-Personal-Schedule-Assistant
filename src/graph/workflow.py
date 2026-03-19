import os
from datetime import datetime
from dotenv import load_dotenv
from src.tools.google_calendar import calendar_tools
from src.tools.user_db import get_user_info
from src.tools.web_search import research_topic
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
load_dotenv()


def create_scheduling_workflow():
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise ValueError("Chưa tìm thấy HF_TOKEN trong file .env!")

    model = ChatOpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=hf_token,
        model="Qwen/Qwen2.5-72B-Instruct",
        temperature=0
    )

    all_tools = calendar_tools + [get_user_info, research_topic]

    # LẤY THỜI GIAN THỰC TẾ CỦA HỆ THỐNG
    now = datetime.now()
    current_time_str = now.strftime("%A, ngày %d tháng %m năm %Y, %H:%M")

    # Đưa thời gian thực vào System Prompt để AI tính toán
    system_prompt = f"""Bạn là trợ lý ảo quản lý lịch trình cá nhân cực kỳ thông minh.

    THÔNG TIN HỆ THỐNG QUAN TRỌNG:
    - Thời gian hiện tại của người dùng đang là: {current_time_str}

    QUY TẮC LÀM VIỆC:
    1. TÍNH TOÁN THỜI GIAN: Khi người dùng nói "ngày mai", "tuần sau" hoặc các mốc thời gian tương đối, BẮT BUỘC phải dùng [Thời gian hiện tại] ở trên để tính ra chính xác ngày, tháng, năm (YYYY-MM-DD). Tuyệt đối không tự bịa ra năm cũ.
    2. TÔN TRỌNG NGƯỜI DÙNG: Luôn lấy đúng khung giờ người dùng yêu cầu để tra cứu và đặt lịch. 
    3. SỬ DỤNG TOOL: Dùng công cụ Google Calendar để kiểm tra xem giờ đó có bị trùng lịch không. 
    4. ĐỀ XUẤT: Sau khi kiểm tra, tổng hợp lại bằng tiếng Việt (Thời gian chính xác, địa điểm, sự kiện) và hỏi: "Bạn có đồng ý để tôi tạo lịch này trên Google Calendar không?".
    5. TẠO LỊCH: Chỉ dùng tool tạo sự kiện khi người dùng gõ "Đồng ý", "OK", "Tạo đi". Khi gọi tool, phải truyền đúng định dạng ngày giờ chuẩn.
    """

    app = create_react_agent(
        model,
        tools=all_tools,
        prompt=system_prompt,
        checkpointer=MemorySaver()
    )

    return app