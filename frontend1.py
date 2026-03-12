import streamlit as st
import uuid
from agents import main_agent

st.set_page_config(page_title="AI Schedule Agent", layout="wide")

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

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Ô nhập liệu
if prompt := st.chat_input("Hôm nay tôi có lịch gì không?"):
    # Hiển thị tin nhắn người dùng
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Xử lý bằng Multi-agent
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        # Cấu hình thread_id cho LangGraph
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        inputs = {"messages": [("human", prompt)]}

        # Chạy stream để bắt các bước suy nghĩ của Agent
        with st.spinner("Đang xử lí..."):
            for chunk in main_agent.stream(inputs, config=config, stream_mode="updates"):
                for node, value in chunk.items():
                    st.caption(f"⚙️ Node: {node} đang xử lý...")
                    if "messages" in value:
                        full_response = value["messages"][-1].content

        placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})