from langchain_google_community import CalendarToolkit

def get_calendar_tools():
    """Khởi tạo và lấy danh sách các công cụ Google Calendar an toàn"""
    try:
        # Phiên bản mới của LangChain tự động quản lý kết nối bên trong CalendarToolkit
        toolkit = CalendarToolkit()
        return toolkit.get_tools()
    except Exception as e:
        print(f"⚠️ Cảnh báo: Lỗi khởi tạo Google Calendar API (Kiểm tra lại credentials.json hoặc token.json). Chi tiết: {e}")
        return []