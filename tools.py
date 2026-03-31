from langchain_core.tools import tool

@tool
def get_current_schedule(date: str):
    """Lấy danh sách các sự kiện trong ngày. Định dạng date: YYYY-MM-DD."""
    # Sau này viết code SQL hoặc gọi API ở đây
    return f"Lịch ngày {date}: 09:00 - Họp phòng, 14:00 - Học tiếng Anh."

@tool
def add_event_to_calendar(event_details: str):
    """Thêm một sự kiện mới vào lịch."""
    return f"Đã ghi nhận vào hệ thống: {event_details}"

@tool
def analyze_free_time(schedule_context: str):
    """Phân tích các khoảng trống trong lịch trình để tìm giờ nghỉ."""
    return "Dựa trên lịch trình, bạn trống từ 10:00-14:00 và sau 15:00."