import streamlit as st
import uuid
from dotenv import load_dotenv

# 1. Import workflow chuẩn từ thư mục src
from src.graph.workflow import create_scheduling_workflow

# Tải biến môi trường
load_dotenv()


@st.cache_resource
def get_graph():
    return create_scheduling_workflow()


main_agent = get_graph()

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="AI Schedule Agent", page_icon="📅", layout="centered")
st.title("📅 AI Personal Schedule Assistant")

# 3. Khởi tạo Session State (Bộ nhớ của Streamlit)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())  # Tạo ID duy nhất cho mỗi phiên chat để LangGraph nhớ ngữ cảnh

# Sidebar hiển thị thông tin
with st.sidebar:
    st.header("🤖 System Status")
    st.info(f"Thread ID: {st.session_state.thread_id}")
    st.caption("Dùng Groq/Llama3.2/Qwen + LangGraph")

    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

# 4. Hiển thị lịch sử chat trên màn hình
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Ô nhập liệu và xử lý logic
if prompt := st.chat_input("Hôm nay tôi có lịch gì không? Hay lên lịch meeting Q1 nhé..."):

    # Hiển thị tin nhắn người dùng ngay lập tức
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Khung xử lý của Assistant
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        # Cấu hình thread_id cho LangGraph
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        inputs = {"messages": [("user", prompt)]}

        # Tạo một khung status để show các bước Agent đang làm
        with st.status("Đang phân tích yêu cầu...", expanded=True) as status:
            try:
                # Chạy stream để bắt các bước suy nghĩ của Agent
                for chunk in main_agent.stream(inputs, config=config, stream_mode="updates"):
                    for node_name, value in chunk.items():
                        # Cập nhật trạng thái đang chạy Node nào
                        st.write(f"⚙️ Đang xử lý tại: **{node_name}**...")

                        # Bóc tách tin nhắn từ Node
                        if "messages" in value and value["messages"]:
                            last_msg = value["messages"][-1]
                            # Xử lý an toàn vì LangChain có thể trả về Object AIMessage hoặc chuỗi
                            if hasattr(last_msg, 'content'):
                                full_response = last_msg.content
                            else:
                                full_response = str(last_msg)

                status.update(label="Đã hoàn tất suy luận!", state="complete", expanded=False)

            except Exception as e:
                st.error(f"Hệ thống gặp sự cố: {e}")
                status.update(label="Lỗi xử lý", state="error", expanded=False)

        # Hiển thị kết quả cuối cùng ra UI
        if full_response:
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})