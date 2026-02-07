import streamlit as st
from backend import function1 as f
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Personal Schedule Agent", page_icon="🤖", layout="centered")

# --- SIDEBAR CHỈ ĐỂ HIỂN THỊ METRIC ---
with st.sidebar:
    st.header("📊 Trạng thái hệ thống")
    is_connected, latency, error_msg = f.check_api_latency()
    if is_connected:
        st.metric(label="Độ trễ API (Latency)", value=f"{latency} ms", delta="Online")
    else:
        st.metric(label="Trạng thái API", value="Offline", delta="Lỗi", delta_color="inverse")
    st.divider()
    st.caption("Agent: Qwen3-235B-A22B")

# CSS để tối ưu giao diện: Làm mờ viền uploader và sát khung chat
st.markdown("""
    <style>
    .stChatFloatingInputContainer { bottom: 20px; }
    /* Thu gọn khoảng cách giữa uploader và chat input */
    .stFileUploader { padding-bottom: 0px; }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Personal Schedule Agent")
st.caption("Trợ lý AI đồng bộ trực tiếp với Google Calendar và tài liệu của bạn")

# Khởi tạo tin nhắn
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Chào bạn! Tui đã sẵn sàng. Bạn có thể gửi tin nhắn hoặc đính kèm tài liệu ngay bên dưới."}]

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- KHU VỰC UPLOAD FILE (NẰM TRÊN TEXTBOX) ---
uploaded_file = st.file_uploader("", type=["pdf", "txt", "docx"], label_visibility="collapsed")

if uploaded_file:
    # Xử lý khi có file mới được tải lên
    if "last_uploaded_file" not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
        st.session_state.messages.append({"role": "user", "content": f"📎 Đã tải lên file: {uploaded_file.name}"})
        st.session_state.last_uploaded_file = uploaded_file.name
        
        with st.chat_message("assistant"):
            with st.spinner("Đang trích xuất tri thức từ file..."):
                # Tại đây bạn sẽ gọi logic RAG để băm nhỏ file và lưu vào Vector DB
                # f.ingest_to_rag(uploaded_file)
                time.sleep(1)
                st.write(f"✅ Tui đã đọc xong tài liệu **{uploaded_file.name}**. Giờ bạn có thể hỏi về nội dung này!")

# --- Ô NHẬP LIỆU CHÍNH ---
if prompt := st.chat_input("Nhập lịch trình hoặc sửa đổi các lịch trình..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Qwen3 đang xử lý..."):
            # Gọi AI trích xuất thông tin
            data = f.extract_info_with_qwen(prompt)
            
            if data:
                # link = f.save_to_google_calendar(data, prompt)
                link = None 
                
                if link:
                    response = f"✅ Đã thêm sự kiện: **{data['event_name']}** vào Google Calendar!\n\n🔗 [Xem trên lịch]({link})"
                else:
                    response = f"🎯 Đã nhận diện lịch trình: **{data['event_name']}** vào lúc **{data['start_time']}**."
            else:
                response = "😅 Tui đang lắng nghe đây, bạn muốn lên lịch hay hỏi gì về file đã upload không?"
            
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})