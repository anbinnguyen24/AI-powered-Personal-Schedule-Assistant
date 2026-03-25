from langchain_core.tools import tool

@tool
def get_user_info() -> str:
    """Lấy thông tin và múi giờ của người dùng."""
    return '{"name": "Người dùng", "timezone": "Asia/Ho_Chi_Minh", "note": "Ưu tiên theo thời gian yêu cầu"}'