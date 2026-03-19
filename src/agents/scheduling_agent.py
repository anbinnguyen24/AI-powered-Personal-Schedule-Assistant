from src.tools.google_calendar import calendar_tools
schedule_subagent = {
    "name": "schedule-agent",
    "description": "Lên lịch sau khi có approval",
    "system_prompt": """Bạn chuyên gia lên lịch. Luồng:
    1. Đề xuất lịch trình dựa trên availability
    2. Gửi proposal cho human approve
    3. Chỉ tạo event sau khi approve
    4. Confirm với user.""",
    "tools": [calendar_tools]
}