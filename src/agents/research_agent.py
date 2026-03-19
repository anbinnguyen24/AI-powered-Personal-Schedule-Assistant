from src.tools.web_search import research_topic
from src.tools.user_db import get_user_info

research_subagent = {
    "name": "research-agent",
    "description": "Nghiên cứu thông tin user và event",
    "system_prompt": """Bạn là chuyên gia nghiên cứu. Nhiệm vụ:
    1. Tìm thông tin user (timezone, sở thích)
    2. Nghiên cứu chi tiết về event/topic
    3. Trả về dữ liệu có cấu trúc.""",
    "tools": [get_user_info, research_topic]
}