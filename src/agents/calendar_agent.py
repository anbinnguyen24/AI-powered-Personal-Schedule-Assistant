from src.tools.google_calendar import calendar_tools

calendar_subagent = {
    "name": "calendar-agent",
    "description": "Kiểm tra lịch trống Google Calendar",
    "system_prompt": """Bạn chuyên gia lịch trình. Nhiệm vụ:
    1. Check free slots trong date range
    2. Đề xuất 3-5 slots tốt nhất
    3. Xem xét timezone và user prefs.""",
    "tools": [calendar_tools]
}