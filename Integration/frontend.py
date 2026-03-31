import streamlit as st
import uuid
import time
from datetime import datetime
import os

from streamlit_autorefresh import st_autorefresh

from agents import get_main_agent
from tools import get_vector_db

# =====================================
# CONFIG
# =====================================

TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_files")
os.makedirs(TEMP_DIR, exist_ok=True)

st.set_page_config(page_title="AI Schedule Agent", layout="wide")

# =====================================
# SESSION STATE INIT
# =====================================


if "all_data" not in st.session_state:
    db = get_vector_db()
    st.session_state.all_data = db.get(include=["documents", "metadatas"])

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())


# ✅ FLAG CHỐNG RERUN GỌI TOOL LẶP
if "agent_ran" not in st.session_state:
    st.session_state.agent_ran = False


# =====================================
# REMINDER CHECK
# =====================================
if st.session_state.agent_ran:
    st_autorefresh(interval=60000, key="schedule_refresh")
current_ts = int(time.time())

# Lấy dữ liệu từ bộ nhớ đệm (RAM) ra để dùng cho toàn bộ file
all_data = st.session_state.all_data

if all_data and all_data.get("metadatas"):
    for i, meta in enumerate(all_data["metadatas"]):
        if meta and "reminder_timestamp" in meta:
            rem_ts = int(meta["reminder_timestamp"])

            current_time_str = datetime.fromtimestamp(current_ts).strftime("%Y-%m-%d %H:%M")
            rem_time_str = datetime.fromtimestamp(rem_ts).strftime("%Y-%m-%d %H:%M")

            if current_time_str == rem_time_str:
                event_text = all_data["documents"][i]
                st.toast(f"⏰ **ĐẾN GIỜ RỒI:** {event_text}", icon="🔔")


# =====================================
# EVENT DETAIL DIALOG
# =====================================

@st.dialog("📋 CHI TIẾT SỰ KIỆN")
def show_event_details(meta, doc, current_ts):
    start_time = meta.get("start_time", "Chưa xác định")
    end_time = meta.get("end_time", "Chưa xác định")
    location = meta.get("location", "Chưa xác định")
    event_name = meta.get("event_name", "Sự kiện")
    reminder = meta.get("reminder_minutes", 0)
    rem_ts = meta.get("reminder_timestamp", 0)

    status = "Chưa đến giờ nhắc ⏳"
    if rem_ts and current_ts >= int(rem_ts):
        status = "Đã nhắc ✅"

    st.markdown(f"**📌 Tên sự kiện:** {event_name}")
    st.markdown(f"**📍 Địa điểm:** {location}")
    st.markdown(f"**▶️ Bắt đầu:** {start_time}")
    st.markdown(f"**⏹️ Kết thúc:** {end_time}")
    st.markdown(f"**🔔 Nhắc trước:** {reminder} phút")
    st.markdown(f"**📊 Trạng thái:** {status}")

    if st.button("❌ Đóng cửa sổ", use_container_width=True):
        st.rerun()


# =====================================
# SIDEBAR
# =====================================

with st.sidebar:
    st.title("🤖 System Status")
    st.info(f"Thread ID: {st.session_state.thread_id}")

    if st.button("Xóa lịch sử chat"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.agent_ran = False
        st.rerun()

    st.divider()
    st.title("📅 Lịch trình đã lưu")

    if all_data and all_data.get("documents"):
        events_by_date = {}

        for i, doc in enumerate(all_data["documents"]):
            meta = all_data["metadatas"][i]
            date = meta.get("date", "Không xác định")

            events_by_date.setdefault(date, []).append((i, meta, doc))

        sorted_dates = sorted(events_by_date.keys(), reverse=True)

        for date in sorted_dates:
            try:
                date_label = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                date_label = date

            st.markdown(f"**{date_label}**")

            events = sorted(
                events_by_date[date],
                key=lambda x: x[1].get("start_time", "00:00")
            )

            for i, meta, doc in events:
                event_name = meta.get("event_name", "Sự kiện")

                try:
                    time_only = datetime.strptime(
                        meta.get("start_time", "00:00")[:16],
                        "%Y-%m-%d %H:%M"
                    ).strftime("%H:%M")
                except Exception:
                    time_only = "??:??"

                short_name = (event_name[:18] + "..") if len(event_name) > 18 else event_name
                label = f"⏰ {time_only} | {short_name}"

                if st.button(label, key=f"event_btn_{i}", use_container_width=True):
                    show_event_details(meta, doc, current_ts)

            st.divider()
    else:
        st.info("Chưa có lịch trình nào được lưu.", icon="📭")


# =====================================
# CHAT HISTORY
# =====================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "attached_files" in message:
            for f in message["attached_files"]:
                st.caption(f"📎 Đính kèm: {f}")


# =====================================
# CHAT INPUT + AGENT RUN
# =====================================

if user_input := st.chat_input("Hôm nay tui có lịch gì không?", accept_file=True):
    full_response = ""
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    # 1. Lấy text và files cực an toàn, Pylance không bao giờ bắt lỗi được
    prompt = user_input.text if user_input.text else "Xử lý file này giúp tui."
    
    # Dùng "or []" để đảm bảo uploaded_files luôn là List, dập tắt lỗi báo None
    uploaded_files = user_input.files or [] 
    file_names = [f.name for f in uploaded_files]

    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "attached_files": file_names
    })

    st.session_state.agent_ran = False

    with st.chat_message("user"):
        st.markdown(prompt)
        for f in file_names:
            st.caption(f"📎 Đính kèm: {f}")

    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    enhanced_prompt = f"{prompt}\n\n[System: {current_time_str}]"

    if not st.session_state.agent_ran:
        with st.chat_message("assistant"):
            
            # 2. BẬT SPINNER NGAY TẠI ĐÂY (Vừa Enter là loading hiện ra liền)
            with st.spinner("🧠 Agent đang suy nghĩ và thực thi công cụ..."):
                
                # 3. Luồng ghi file vào ổ cứng nằm trọn bên trong Spinner
                for f in uploaded_files:
                    file_path = os.path.join(TEMP_DIR, f.name)
                    with open(file_path, "wb") as out_f:
                        out_f.write(f.read())
                    enhanced_prompt += f"\n\n[File Path: {file_path}]"

                # 4. Bắt đầu gọi Agent
                try:
                    agent = get_main_agent()
                    # Vòng lặp này sẽ chặn (block) code cho đến khi Agent chạy xong toàn bộ (bao gồm cả các tool lưu file/sự kiện)
                    for chunk in agent.stream(
                        {"messages": [("human", enhanced_prompt)]},
                        config=config,
                        stream_mode="updates"
                    ):
                        for node, value in chunk.items():
                            if "messages" in value:
                                msg = value["messages"][-1].content
                                # Đảm bảo msg là text và không bị rỗng thì mới cập nhật
                                if node == "agent" and isinstance(msg, str) and msg.strip():
                                    full_response = msg
                except Exception as e:
                    full_response = f"❌ Lỗi: {str(e)}"
            
            # --- VỪA THOÁT KHỎI SPINNER LÀ LOADING TẮT ---

            if not full_response.strip():
                full_response = "✅ Tui đã xử lý xong yêu cầu của bạn!"
            
            # 3. IN KẾT QUẢ RA NGAY TỨC THÌ (Không có độ trễ)
            st.markdown(full_response)

        # 4. Lưu tin nhắn vào lịch sử
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })

        # 5. Khóa trạng thái để không bị gọi lại
        st.session_state.agent_ran = True

        st.session_state.all_data = get_vector_db().get(include=["documents", "metadatas"])
        st.rerun()