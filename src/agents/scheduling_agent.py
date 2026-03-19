from src.tools.google_calendar import create_event

schedule_subagent = {
    "name": "schedule-agent",
    "description": "Lên lịch sau khi có approval",
    "system_prompt": """Bạn chuyên gia lên lịch. Luồng:
    1. Đề xuất meeting time dựa trên availability
    2. Gửi proposal cho human approve
    3. Chỉ tạo event sau khi approve
    4. Confirm với user.""",
    "tools": [create_event]
}