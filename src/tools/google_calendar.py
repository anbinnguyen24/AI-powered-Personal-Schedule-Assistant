from langchain_google_community import CalendarToolkit
from langchain.tools import tool

@tool
def check_user_availability(email: str, date: str) -> str:
    """Check user's Google Calendar availability."""
    toolkit = CalendarToolkit()
    calendar = toolkit.get_calendar()
    # Logic check availability
    return f"Available slots for {email}: 10AM-11AM, 2PM-3PM"

@tool
def create_event(email: str, title: str, start: str, end: str) -> str:
    """Create Google Calendar event after approval."""
    toolkit = CalendarToolkit()
    # Create event logic
    return f"Created '{title}' from {start} to {end}"