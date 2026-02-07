from openai import OpenAI
import sqlite3
import time
import traceback
import streamlit as st
from datetime import datetime, timedelta
import dateutil.parser
import pandas as pd
import os
import json
from dotenv import load_dotenv

# Cấu hình đường dẫn file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "personal_schedule.db")
load_dotenv(os.path.join(BASE_DIR, '..', '.env'))
# 1. Khởi tạo kết nối duy nhất
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ.get("HF_TOKEN"),
)

# ==========================================
# 🎯 HÀM TỔNG DÙNG CHUNG CHO AI (GOM LẠI THÀNH 1)
# ==========================================
def ask_qwen(model, messages, temperature=0.1, max_tokens=None):
    """
    Hàm duy nhất để giao tiếp với Qwen.
    Trả về: (Nội dung phản hồi, Latency ms) hoặc (None, 0) nếu lỗi.
    """
    start_time = time.time()
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        latency = round((time.time() - start_time) * 1000)
        return completion.choices[0].message.content, latency
    except Exception as e:
        print(f"❌ Lỗi API: {e}")
        return None, 0

# ==========================================
# 🟢 PHẦN CẬP NHẬT: SỬ DỤNG HÀM CHUNG
# ==========================================

def check_api_latency():
    """
    Kiểm tra kết nối bằng hàm ask_qwen
    """
    # Dùng model nhẹ hoặc model chính để check
    response, latency = ask_qwen(
        model="Qwen/Qwen3-235B-A22B", 
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=1
    )
    if response is not None:
        return True, latency, None
    return False, 0, "Không thể kết nối API"

def extract_info_with_qwen(user_input):
    """
    Trích xuất lịch trình sử dụng hàm ask_qwen
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    weekday = datetime.now().strftime("%A")
    
    system_prompt = f"""
    Bạn là một trợ lý ảo giúp trích xuất thông tin lịch trình từ văn bản.
    Thời gian hiện tại là: {current_time} ({weekday}).
    Trả về JSON: event_name, start_time, end_time, location, reminder_minutes.
    """

    # Bạn có thể đổi sang model Qwen3-235B-A22B:novita nếu muốn "não to" hơn
    content, _ = ask_qwen(
        model="Qwen/Qwen3-235B-A22B:novita", 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )
    
    if content:
        try:
            # Xử lý dọn dẹp markdown nếu AI trả về ```json ... ```
            clean_content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_content)
        except Exception as e:
            print(f"Lỗi parse JSON: {e}")
    return None

# ==========================================
# CÁC PHẦN CÒN LẠI (GIỮ NGUYÊN)
# ==========================================

def render_api_status_sidebar():
    with st.sidebar:
        st.divider()
        st.write("🔌 **Trạng thái Server AI**")
        if st.button("Ping API", use_container_width=True):
            with st.spinner("Đang kết nối..."):
                is_connected, latency, error = check_api_latency()
            if is_connected:
                st.success(f"✅ Online ({latency}ms)")
            else:
                st.error(f"❌ Lỗi: {error}")

# --- Các hàm Database và UI bên dưới giữ nguyên như file function1.py của bạn ---
def init_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                reminder_minutes INTEGER,
                preprocessed_text TEXT,
                is_reminded INTEGER DEFAULT 0
            )''')
            print("Đã khởi tạo Database thành công.")
    except Exception as e:
        print(f"Lỗi khởi tạo DB: {e}")
        traceback.print_exc()
        raise e


def load_all_schedules():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            return pd.read_sql_query("SELECT * FROM schedules ORDER BY start_time DESC", conn)
    except Exception as e:
        print(f"Lỗi khi tải lịch trình: {e}")
        traceback.print_exc()
        return pd.DataFrame()


def save_schedule_to_db(data_dict, text):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO schedules (event_name, start_time, end_time, location, preprocessed_text, reminder_minutes) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    data_dict.get('event_name'),
                    data_dict.get('start_time'),
                    data_dict.get('end_time'),
                    data_dict.get('location'),
                    text,
                    data_dict.get('reminder_minutes')
                )
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"Lỗi khi lưu vào DB: {e}")
        traceback.print_exc()
        raise Exception(f"Lỗi lưu dữ liệu: {str(e)}")


def delete_schedule(row_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("DELETE FROM schedules WHERE id = ?", (row_id,))
            conn.commit()
        return True
    except Exception as e:
        print(f"Lỗi khi xóa: {e}")
        traceback.print_exc()
        raise Exception(f"Không thể xóa dòng {row_id}: {str(e)}")


def update_schedule(row_id, data_dict, text):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "UPDATE schedules SET event_name=?, start_time=?, end_time=?, location=?, preprocessed_text=?, reminder_minutes=?, is_reminded=0 WHERE id=?",
                (data_dict.get('event_name'),
                    data_dict.get('start_time'),
                    data_dict.get('end_time'),
                    data_dict.get('location'),
                    text,
                    data_dict.get('reminder_minutes'),
                    row_id)
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"Lỗi cập nhật: {e}")
        traceback.print_exc()
        raise Exception(f"Lỗi cập nhật ID {row_id}: {str(e)}")


def query_events_from_db(criteria: dict):
    print(f"\n--- DEBUG QUERY ---")
    print(f"Input Criteria: {criteria}")

    conditions = []
    params = []

    # 1. Tìm theo từ khóa (Tên hoặc địa điểm)
    if criteria.get("general_keyword"):
        keyword = criteria["general_keyword"]
        conditions.append("(event_name LIKE ? OR location LIKE ?)")
        params.append(f"%{keyword}%")
        params.append(f"%{keyword}%")

    # 2. Tìm theo thời gian bắt đầu
    if criteria.get("start_time"):
        target_dt = criteria["start_time"]
        start_of_day = datetime.combine(target_dt.date(), datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        conditions.append("datetime(start_time) >= datetime(?)")
        conditions.append("datetime(start_time) < datetime(?)")
        params.append(start_of_day.isoformat(sep=' '))
        params.append(end_of_day.isoformat(sep=' '))

    # 3. [QUAN TRỌNG] Tìm theo số phút nhắc nhở
    if criteria.get("reminder_minutes") is not None:
        print(f"-> Có điều kiện tìm phút: {criteria['reminder_minutes']}")
        conditions.append("reminder_minutes = ?")
        params.append(criteria["reminder_minutes"])

    # Xây dựng SQL
    base_query = "SELECT id, event_name, location, start_time, end_time, reminder_minutes, preprocessed_text, is_reminded FROM schedules"

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
        print(f"-> SQL: {base_query}")
        print(f"-> Params: {params}")
    else:
        print("-> Không có điều kiện nào -> Trả về rỗng.")
        return []

    base_query += " ORDER BY start_time DESC"

    results = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(base_query, tuple(params))
            rows = cursor.fetchall()
            print(f"-> Tìm thấy: {len(rows)} kết quả.")
            for row in rows:
                results.append(dict(row))
    except Exception as e:
        print(f"Lỗi query DB: {e}")
        return []

    return results


# Hàm kiểm tra nhắc nhở (Logic nghiêm ngặt)
def check_reminders_now():
    events = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Chỉ lấy các sự kiện chưa được nhắc (is_reminded = 0)
            cursor.execute("SELECT * FROM schedules WHERE is_reminded = 0")
            now = datetime.now()

            rows = cursor.fetchall()
            for row in rows:
                try:
                    evt_time = dateutil.parser.parse(row['start_time'])
                    remind_before = int(row['reminder_minutes'] or 0)

                    # Tính thời điểm cần báo
                    # Ví dụ: Sự kiện 10:00, nhắc trước 20p -> Trigger lúc 09:40
                    trigger_time = evt_time - timedelta(minutes=remind_before)

                    # Logic cửa sổ 1 phút
                    # Chỉ báo khi thời gian hiện tại nằm trong phút đó (từ 00s đến 59s)
                    # Nếu trễ quá 1 phút (now >= trigger + 1 phút) -> Bỏ qua luôn (coi như miss)
                    if trigger_time <= now < (trigger_time + timedelta(minutes=1)):
                        events.append(dict(row))
                        # Đánh dấu đã báo để không báo lại liên tục trong 1 phút đó
                        conn.execute("UPDATE schedules SET is_reminded=1 WHERE id=?", (row['id'],))
                        conn.commit()

                except Exception as parse_err:
                    print(f"Lỗi parse ngày tháng tại ID {row['id']}: {parse_err}")
                    continue
    except Exception as e:
        print(f"Check reminder error: {e}")
        pass
    return events


# Hàm chính gọi API và hiển thị Dialog

@st.dialog("Kết quả trích xuất")
def show_result(item, text):
    """
    Hiển thị kết quả và nút LƯU nằm bên trong Dialog
    """
    st.info("Kiểm tra thông tin trước khi lưu:")

    # Hiển thị dictionary dạng code để debug
    st.code(item, language="python")

    st.divider()

    # Hiển thị đẹp
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"🔹 **Sự kiện:** {item.get('event_name')}")
        st.write(f"🔹 **Bắt đầu:** {item.get('start_time')}")
        st.write(f"🔹 **Kết thúc:** {item.get('end_time')}")
    with col2:
        st.write(f"📍 **Địa điểm:** {item.get('location')}")
        st.write(f"⏰ **Nhắc trước:** {item.get('reminder_minutes')} phút")

    st.divider()

    # Nút Lưu nằm ở đây
    col_save, col_cancel = st.columns([1, 1])
    with col_save:
        if st.button("✅ Xác nhận Lưu", use_container_width=True, type="primary"):
            try:
                save_schedule_to_db(item, text)
                st.success("Đã lưu thành công!")
                time.sleep(1.5)
                st.rerun()  # Tải lại trang
            except Exception as e:
                st.error(f"Lỗi: {e}")

    with col_cancel:
        if st.button("Hủy bỏ", use_container_width=True):
            st.rerun()


def get_schedule_dict():
    """
    Gọi trực tiếp hàm xử lý AI và hiển thị Dialog
    """
    user_input = st.session_state.input.strip()
    if not user_input:
        return

    with st.spinner("Đang để Qwen3 phân tích lịch trình..."):
        try:
            # Gọi trực tiếp hàm bạn đã viết ở trên
            result_data = extract_info_with_qwen(user_input)

            if result_data:
                # Nếu AI trả về dữ liệu thành công
                show_result(result_data, user_input)
            else:
                show_error("AI không thể trích xuất thông tin. Hãy thử nhập rõ ràng hơn.")
                
        except Exception as e:
            show_error(f"Lỗi xử lý: {str(e)}")
            traceback.print_exc()


def clear_input():
    st.session_state.input = ""


def show_error(msg):
    st.toast(f"❌ {msg}")