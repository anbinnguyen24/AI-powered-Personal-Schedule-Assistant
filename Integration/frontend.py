import streamlit as st
import uuid
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from agents import main_agent
from tools import vector_db

st.set_page_config(page_title="AI Schedule Agent", layout="wide")

# Thiết lập tự động làm mới giao diện mỗi 60 giây (60000 milliseconds) để kiểm tra nhắc nhở
count = st_autorefresh(interval=60000, limit=None, key="schedule_refresher")

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

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Ô nhập liệu (nằm ở nửa cuối file frontend.py)
if user_input := st.chat_input("Hôm nay tôi có lịch gì không?", accept_file=True):
    prompt = user_input.text if user_input.text else "Đã gửi tệp đính kèm."
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        if user_input.files:
            for f in user_input.files:
                st.caption(f"📎 Đính kèm: {f.name}")

    with st.chat_message("assistant"):
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # === XỬ LÝ ẢNH QUA OCR NẾU CÓ FILE ===
        if user_input.files:
            with st.spinner("Đang quét chữ trong ảnh (OCR)..."):
                from tools import process_image_and_add_to_calendar
                
                # Đọc byte của file
                image_bytes = user_input.files[0].read()
                
                # Gọi hàm OCR
                image_response = process_image_and_add_to_calendar.invoke({
                    "image_bytes": image_bytes, 
                    "current_time": current_time_str
                })
                
                st.markdown(image_response)
                st.session_state.messages.append({"role": "assistant", "content": image_response})
            st.rerun() 
            
        # === XỬ LÝ TEXT ===
        else:
            placeholder = st.empty()
            full_response = ""
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            enhanced_prompt = f"{prompt}\n\n[Thông tin hệ thống ẩn: Thời gian thực tế ngay lúc này là {current_time_str}. BẮT BUỘC dùng mốc này làm chuẩn để tính toán event_time, tuyệt đối không tự bịa năm cũ.]"
            
            inputs = {"messages": [("human", enhanced_prompt)]}
        # Chạy stream để bắt các bước suy nghĩ của Agent
        with st.spinner("Đang xử lí..."):
            try:
                for chunk in main_agent.stream(inputs, config=config, stream_mode="updates"):
                    for node, value in chunk.items():
                        st.caption(f"⚙️ Node: {node} đang xử lý...")
                        if "messages" in value:
                            full_response = value["messages"][-1].content
            except ValueError as e:
                if "tool_calls" in str(e) and "ToolMessage" in str(e):
                    # Lịch sử chat bị hỏng, reset thread_id
                    st.session_state.thread_id = str(uuid.uuid4())
                    st.session_state.messages = []
                    st.warning("⚠️ Phiên chat trước bị lỗi, đã tự động tạo phiên mới. Vui lòng nhập lại yêu cầu.")
                    st.rerun()
                else:
                    raise e

        placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()