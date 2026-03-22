"""
Preferences — Dữ liệu mặc định cho user preferences.
Agent sử dụng built-in filesystem tools (read_file, write_file, edit_file)
để đọc/ghi /memories/user_preferences.txt qua StoreBackend.
"""

import json


# ── Default preferences (dùng để seed lần đầu) ───────────────
DEFAULT_PREFERENCES = {
    "name": "Nael",
    "timezone": "Asia/Ho_Chi_Minh",
    "role": "Sinh viên CNTT",
    "habits": {
        "wake_up": "06:30",
        "sleep": "23:00",
        "study_peak": "08:00-11:00 và 19:00-22:00",
        "exercise": "17:00-18:00 (thứ 2, 4, 6)",
        "lunch": "11:30-13:00",
        "dinner": "18:00-19:00",
    },
    "preferences": {
        "study_session_max": "2 tiếng liên tục, nghỉ 15 phút",
        "meeting_preference": "Online qua Google Meet",
        "priority": "Ưu tiên học bài và làm đồ án",
        "avoid": "Không xếp lịch trước 7h sáng và sau 22h tối",
    },
    "free_time": {
        "weekday": "12:30-14:00, 21:00-23:00",
        "weekend": "08:00-11:00, 14:00-22:00",
    },
    "courses": [
        "Trí tuệ nhân tạo (AI)",
        "Xử lý ngôn ngữ tự nhiên (NLP)",
        "Đồ án chuyên ngành",
    ],
}

DEFAULT_PREFERENCES_TEXT = json.dumps(DEFAULT_PREFERENCES, ensure_ascii=False, indent=2)
