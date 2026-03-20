import streamlit as st
import uuid
from dotenv import load_dotenv
from src.graph.workflow import create_scheduling_workflow
import src.rag_pipeline as rag

load_dotenv()


@st.cache_resource
def get_graph():
    return create_scheduling_workflow()


main_agent = get_graph()

st.set_page_config(page_title="AI Schedule & RAG Agent", page_icon="📅", layout="centered")
st.title("📅 AI Personal Schedule & Advisor (RAG)")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

with st.sidebar:
    st.header("System Controls")
    st.info(f"Thread ID: {st.session_state.thread_id[:8]}...")

    st.divider()
    st.write("**Quản lý Dữ liệu (RAG)**")
    if st.button("Nạp file PDF vào Vector DB", type="primary", use_container_width=True):
        with st.spinner("Đang đọc và băm tài liệu..."):
            success = rag.build_vector_database()
            if success:
                st.success("Nạp dữ liệu RAG thành công!")
            else:
                st.error("Lỗi: Không tìm thấy PDF trong thư mục data/")

    st.divider()
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("VD: Đặt lịch họp dự án chiều mai. Công ty có cho phép họp sau 5h không?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        inputs = {"messages": [("user", prompt)]}

        with st.status("AI đang xử lý...", expanded=True) as status:
            try:
                for chunk in main_agent.stream(inputs, config=config, stream_mode="updates"):
                    for node_name, value in chunk.items():
                        st.write(f"⚙️ Action: **{node_name}**...")
                        if "messages" in value and value["messages"]:
                            last_msg = value["messages"][-1]
                            if hasattr(last_msg, 'content'):
                                full_response = last_msg.content
                            else:
                                full_response = str(last_msg)

                status.update(label="Đã hoàn tất!", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Hệ thống gặp sự cố: {e}")
                status.update(label="Lỗi xử lý", state="error", expanded=False)

        if full_response:
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})