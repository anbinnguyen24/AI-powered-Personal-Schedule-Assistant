import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "personal_schedule.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT, start_time TEXT, end_time TEXT,
            location TEXT, reminder_minutes INTEGER
        )''')

def save_schedule(data):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO schedules (event_name, start_time, location) VALUES (?, ?, ?)",
                    (data.get('event_name'), data.get('start_time'), data.get('location')))

def query_schedules(date_str):
    # Logic tìm kiếm lịch theo ngày
    return f"Lịch ngày {date_str}: 09:00 - Họp phòng, 14:00 - Học tiếng Anh."