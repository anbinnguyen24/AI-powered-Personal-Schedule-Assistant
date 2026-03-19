from langchain.tools import tool
@tool
def get_user_info(user_id: str) -> str:
    """Get user preferences and timezone."""
    # Your user database logic
    return '{"name": "John", "timezone": "UTC+7", "pref": "morning"}'