# tools.py
import re
from typing import List, Dict, Optional

# --- Tool 1: Lấy lịch hiện tại (giả lập) ---

calendar_db = {
    "demo_user": [
        {"date": "2023-09-01", "time": "10:00", "event": "Học tập"},
        {"date": "2023-09-01", "time": "14:00", "event": "Họp nhóm"},
        {"date": "2026-03-25", "time": "10:00", "event": "Học tập"},]}


def normalize_time_string(raw_time: str) -> Optional[str]:
    if not raw_time:
        return None

    token = str(raw_time).strip().lower().replace("giờ", "h").replace(" ", "")

    match_colon = re.match(r"^(\d{1,2}):(\d{1,2})$", token)
    if match_colon:
        hour = int(match_colon.group(1))
        minute = int(match_colon.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
        return None

    match_h = re.match(r"^(\d{1,2})h(\d{1,2})?$", token)
    if match_h:
        hour = int(match_h.group(1))
        minute = int(match_h.group(2)) if match_h.group(2) else 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
        return None

    match_hour = re.match(r"^(\d{1,2})$", token)
    if match_hour:
        hour = int(match_hour.group(1))
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"

    return None


# --- Tool 2: Thêm sự kiện vào lịch ---
def add_calendar_event(user_id, event):
    event_to_save = dict(event)
    normalized_time = normalize_time_string(event_to_save.get("time", ""))
    if normalized_time:
        event_to_save["time"] = normalized_time

    calendar_db[user_id].append(event_to_save)
    return f"Sự kiện '{event_to_save.get('event', event_to_save.get('content'))}' đã được lưu"

def get_calendar_events(user_id):
    return calendar_db.get(user_id, [])

# --- Tool 3: Kiểm tra xung đột ---
def check_schedule_conflict(proposed_event: Dict, existing_events: List[Dict]):
    if not proposed_event:
        return None

    if "date" not in proposed_event or "time" not in proposed_event:
        return None  # bỏ qua nếu không đủ dữ liệu

    proposed_time = normalize_time_string(proposed_event.get("time", ""))
    if not proposed_time:
        return None

    for ev in existing_events:
        ev_time = normalize_time_string(ev.get("time", ""))
        if ev.get("date") == proposed_event.get("date") and ev_time == proposed_time:
            return ev  # trả về event bị trùng

    return None

# --- Tool 4: Format lịch trình đẹp ---
def format_schedule(events: List[Dict]) -> str:
    return "\n".join([f"{ev['date']} {ev['time']}: {ev['event']}" for ev in events])