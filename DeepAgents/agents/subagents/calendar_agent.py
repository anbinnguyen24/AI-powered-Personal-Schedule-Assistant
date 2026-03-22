from DeepAgents.prompts.calendar_agent import CALENDAR_AGENT_PROMPT
from DeepAgents.tools.calendar_tool import get_calendar_tools

calendar_subagent = {
    "name": "calendar-agent",
    "description": (
        "Quản lý lịch trình trên Google Calendar: xem, tìm kiếm, tạo, "
        "cập nhật, di chuyển và xóa sự kiện. "
        "Dùng agent này khi cần biết ngày/giờ nào đang bận hoặc rảnh, "
        "hoặc khi cần thao tác với sự kiện trên lịch."
    ),
    "system_prompt": CALENDAR_AGENT_PROMPT,
    "tools": get_calendar_tools(),
    "interrupt_on": {
        # "create_calendar_event": True,
        "update_calendar_event": True,
        "delete_calendar_event": True,
        "move_calendar_event": True,
    },
}
