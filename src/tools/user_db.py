from langchain.tools import tool

@tool
def get_user_info(user_id: str) -> str:
    """Get user preferences and timezone."""
    # Sửa lại thành tiếng Việt và linh hoạt hơn
    return '{"name": "Bạn", "timezone": "Asia/Ho_Chi_Minh", "note": "Luôn ưu tiên làm theo thời gian người dùng yêu cầu."}'