import streamlit as st
import uuid
from langchain_core.messages import HumanMessage, AIMessage
from src.graph.workflow import app

st.set_page_config(page_title="Trợ lý Lịch trình AI", page_icon="📅")
st.title("📅 Trợ lý Quản lý Lịch trình Thông minh")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

config = {"configurable": {"thread_id": st.session_state.thread_id}}

for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

if prompt := st.chat_input("Nhập yêu cầu (VD: Tìm tin tức hôm nay / Lên lịch học)..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI đang xử lý..."):
            try:
                events = app.stream(
                    {"messages": [HumanMessage(content=prompt)]},
                    config=config,
                    stream_mode="values"
                )

                final_response = ""
                for event in events:
                    if "messages" in event:
                        latest_msg = event["messages"][-1]
                        if latest_msg.type != "human":
                            final_response = latest_msg.content

                if final_response:
                    st.markdown(final_response)
                    st.session_state.messages.append(AIMessage(content=final_response))
            except Exception as e:
                st.error(f"Lỗi hệ thống: {str(e)}\nHãy kiểm tra lại API Key trong file .env")