from langgraph.prebuilt import create_react_agent
from src.tools.google_calendar import get_calendar_tools

def get_calendar_agent(llm):
    tools = get_calendar_tools()
    system_message = (
        "Bạn là chuyên gia quản lý lịch trình. Bạn có quyền truy cập vào Google Calendar. "
        "Hãy giúp người dùng kiểm tra sự kiện, thêm lịch mới hoặc chỉnh sửa lịch hiện có. "
        "Luôn xác nhận lại thời gian cụ thể với người dùng trước khi tạo lịch."
    )
    return create_react_agent(llm, tools, state_modifier=system_message)