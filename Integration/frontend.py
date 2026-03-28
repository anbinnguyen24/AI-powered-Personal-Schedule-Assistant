import streamlit as st
import uuid
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from agents import main_agent
from tools import vector_db
import os

TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_files")
os.makedirs(TEMP_DIR, exist_ok=True)

st.set_page_config(page_title="AI Schedule Agent", layout="wide")

# Thiết lập tự động làm mới giao diện mỗi 60 giây (60000 milliseconds) để kiểm tra nhắc nhở
# count = st_autorefresh(interval=60000, limit=None, key="schedule_refresher")

# --- HỆ THỐNG NHẮC NHỞ TỰ ĐỘNG ---
# Kiểm tra thời gian lúc này và quét Vector DB mỗi lần chạy lại giao diện 
current_ts = int(time.time())
all_data = vector_db.get()

if all_data and all_data.get("metadatas"):
    for i, meta in enumerate(all_data["metadatas"]):
        # Nếu sự kiện có lưu thời điểm nhắc nhở
        if meta and "reminder_timestamp" in meta:

            rem_ts = int(meta["reminder_timestamp"])
            
            # Chuyển cả 2 mốc thời gian về định dạng chuỗi "Năm-Tháng-Ngày Giờ:Phút" (cắt bỏ phần giây)
            current_time_str = datetime.fromtimestamp(current_ts).strftime("%Y-%m-%d %H:%M")
            print(f"DEBUG: current_time_str = {current_time_str}")
            rem_time_str = datetime.fromtimestamp(rem_ts).strftime("%Y-%m-%d %H:%M")
            print(f"DEBUG: rem_time_str = {rem_time_str}")
            
            # CÁCH 3: So sánh chính xác đến từng phút
            if current_time_str == rem_time_str:
                event_text = all_data['documents'][i]
                st.toast(f"**⏰ ĐẾN GIỜ RỒI:** {event_text}", icon="🔔")
# ---------------------------------

# --- HÀM HIỂN THỊ CỬA SỔ CHI TIẾT SỰ KIỆN ---
@st.dialog("📋 CHI TIẾT SỰ KIỆN")
def show_event_details(meta, doc, current_ts):
    # Lấy thông tin
    start_time = meta.get("start_time", "Chưa xác định")
    end_time = meta.get("end_time", "Chưa xác định")
    location = meta.get("location", "Chưa xác định")
    event_name = meta.get("event_name", "Sự kiện")
    reminder = meta.get("reminder_minutes", 0)
    rem_ts = meta.get("reminder_timestamp", 0)

    # Tính toán trạng thái "Đã nhắc chưa"
    status = "Chưa đến giờ nhắc ⏳"
    if rem_ts and current_ts >= int(rem_ts):
        status = "Đã nhắc ✅"

    # Hiển thị Form thông tin
    st.markdown(f"**📌 Tên sự kiện:** {event_name}")
    st.markdown(f"**📍 Địa điểm:** {location}")
    st.markdown(f"**▶️ Bắt đầu:** {start_time}")
    st.markdown(f"**⏹️ Kết thúc:** {end_time}")
    st.markdown(f"**🔔 Nhắc trước:** {reminder} phút")
    st.markdown(f"**📊 Trạng thái:** {status}")

    # Nút đóng
    if st.button("❌ Đóng cửa sổ", use_container_width=True):
        st.rerun()


# 1. Khởi tạo Session State (Bộ nhớ của Streamlit)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())  # Tạo ID duy nhất cho mỗi phiên chat

# Sidebar hiển thị thông tin
with st.sidebar:
    st.title("🤖 System Status")
    st.info(f"Thread ID: {st.session_state.thread_id}")
    if st.button("Xóa lịch sử chat"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

    st.divider()
    st.title("📅 Lịch trình đã lưu")
    # Nhóm sự kiện theo ngày
    if all_data and all_data.get("documents"):
        # Tạo dict nhóm theo ngày
        events_by_date = {}
        for i, doc in enumerate(all_data["documents"]):
            meta = all_data["metadatas"][i]
            date = meta.get("date", "Không xác định")
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append((i, meta, doc))
        
        # Sắp xếp ngày từ gần nhất đến xa nhất
        sorted_dates = sorted(events_by_date.keys(), reverse=True)
        
        for date in sorted_dates:
            # Hiển thị header ngày
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                date_label = date_obj.strftime("%d/%m/%Y")
            except:
                date_label = date
            
            st.markdown(f"**{date_label}**")
            
            # Sắp xếp sự kiện trong ngày theo giờ
            events = sorted(events_by_date[date], key=lambda x: x[1].get("start_time", "00:00"))
            
            for i, meta, doc in events:
                event_name = meta.get("event_name", "Sự kiện")
                
                # Lấy giờ:phút (ví dụ: 13:24)
                time_only = datetime.strptime(meta.get("start_time", "00:00"), "%Y-%m-%d %H:%M").strftime("%H:%M")
                # Rút gọn tên nếu quá dài (quá 18 ký tự)
                short_name = (event_name[:18] + '..') if len(event_name) > 18 else event_name
                
                label = f"⏰ {time_only} | {short_name}"
                
                if st.button(label, key=f"event_btn_{i}", use_container_width=True, help=f"Xem chi tiết: {event_name}"):
                    show_event_details(meta, doc, current_ts)
            
            st.divider()
    else:
        st.info("Chưa có lịch trình nào được lưu.", icon="📭")

# --- HIỂN THỊ LỊCH SỬ CHAT (ĐÃ CẬP NHẬT ĐỂ GIỮ FILE) ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Hiển thị lại tên các file đã đính kèm trong lượt chat này
        if "attached_files" in message:
            for f_name in message["attached_files"]:
                st.caption(f"📎 Đính kèm: {f_name}")

# Nhập liệu
if user_input := st.chat_input("Hôm nay tui có lịch gì không?", accept_file=True):
    st.session_state.is_processing = True 
    prompt = user_input.text if user_input.text else "Xử lý file này giúp tui."
    
    # --- LƯU TIN NHẮN VÀO LỊCH SỬ KÈM TÊN FILE ---
    file_names = [f.name for f in user_input.files] if user_input.files else []
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt,
        "attached_files": file_names # Lưu danh sách tên file vào session state
    })
    
    with st.chat_message("user"):
        st.markdown(prompt)
        for f_name in file_names:
            st.caption(f"📎 Đính kèm: {f_name}")

    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    enhanced_prompt = f"{prompt}\n\n[System: {current_time_str}]"

    if user_input.files:
        for f in user_input.files:
            file_path = os.path.join(TEMP_DIR, f.name)
            with open(file_path, "wb") as out_f:
                out_f.write(f.read())
            enhanced_prompt += f"\n\n[File Path: {file_path}]"

    full_response = ""
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    
    with st.status("🧠 Agent đang xử lý...", expanded=True) as status:
        try:
            for chunk in main_agent.stream({"messages": [("human", enhanced_prompt)]}, config=config, stream_mode="updates"):
                for node, value in chunk.items():
                    if "messages" in value:
                        msg_content = value["messages"][-1].content
                        if node == "tools":
                            st.write(f"🛠️ Đang cập nhật cơ sở dữ liệu...")
                        elif node == "agent":
                            if msg_content.strip():
                                if '{"name":' in msg_content and '"parameters":' in msg_content:
                                    st.write("Đang đồng bộ dữ liệu ngầm...")
                                else:
                                    full_response = msg_content

            status.update(label="Xử lý xong!", state="complete", expanded=False)
        except Exception as e:
            full_response = f"❌ Lỗi: {str(e)}"

    if not full_response.strip():
        full_response = "✅ Tui đã xử lý xong yêu cầu của bạn!"

    st.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.session_state.is_processing = False
    st.rerun()