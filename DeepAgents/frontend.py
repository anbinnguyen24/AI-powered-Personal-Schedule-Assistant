import uuid

import streamlit as st
from dotenv import load_dotenv
from langgraph.types import Command

from DeepAgents.agent import create_schedule_advisor

load_dotenv()

# ── Subagent name mapping cho hiển thị đẹp ──
SUBAGENT_DISPLAY = {
    "preference-agent": "🧑 Preference Agent",
    "calendar-agent": "📅 Calendar Agent",
    "rag-agent": "📚 RAG Agent",
}


@st.cache_resource
def init_agent():

    return create_schedule_advisor()


agent, seed_files = init_agent()

st.set_page_config(page_title="AI Schedule & RAG Agent", page_icon="📅", layout="centered")
st.title("📅 AI Personal Schedule & Advisor (RAG)")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "pending_interrupt" not in st.session_state:
    st.session_state.pending_interrupt = None

with st.sidebar:
    st.header("System Controls")
    st.info(f"Thread ID: {st.session_state.thread_id[:8]}...")

    st.divider()
    st.write("**Quản lý Dữ liệu (RAG)**")
    if st.button("Nạp file PDF vào Vector DB", type="primary", use_container_width=True):
        with st.spinner("Đang đọc và băm tài liệu..."):
            try:
                import src.rag_pipeline as rag
                success = rag.build_vector_database()
                if success:
                    st.success("Nạp dữ liệu RAG thành công!")
                else:
                    st.error("Lỗi: Không tìm thấy PDF trong thư mục data/")
            except Exception as e:
                st.error(f"Lỗi: {e}")

    st.divider()
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.pending_interrupt = None
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Human-in-the-loop: Hiển thị UI xác nhận nếu có interrupt ──
if st.session_state.pending_interrupt is not None:
    interrupt_data = st.session_state.pending_interrupt

    with st.container(border=True):
        st.warning("⏸️ **HUMAN REVIEW** — Agent yêu cầu xác nhận")

        # interrupt_data có thể là list hoặc dict tuỳ phiên bản
        action_requests = []
        if isinstance(interrupt_data, dict):
            action_requests = interrupt_data.get("action_requests", [])
        elif isinstance(interrupt_data, list):
            action_requests = interrupt_data

        for action in action_requests:
            if isinstance(action, dict):
                tool_name = action.get("name", "unknown")
                tool_args = action.get("args", {})
            elif hasattr(action, "name"):
                tool_name = action.name
                tool_args = getattr(action, "args", {})
            else:
                tool_name = str(type(action).__name__)
                tool_args = {}

            st.markdown(f"**📋 Tool:** `{tool_name}`")
            if isinstance(tool_args, dict):
                for key, val in tool_args.items():
                    st.markdown(f"  • **{key}:** {val}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Đồng ý thực hiện", type="primary", use_container_width=True):
                decisions = [{"type": "approve"} for _ in action_requests]
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                with st.spinner("Đang thực hiện thao tác lịch..."):
                    try:
                        result = agent.invoke(
                            Command(resume={"decisions": decisions}),
                            config=config, version="v2",
                        )
                        resp = _extract_final_response(result)
                        if resp:
                            st.session_state.messages.append({"role": "assistant", "content": resp})
                    except Exception as e:
                        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Lỗi: {e}"})
                st.session_state.pending_interrupt = None
                st.rerun()

        with col2:
            if st.button("❌ Từ chối", use_container_width=True):
                decisions = [{"type": "reject"} for _ in action_requests]
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                with st.spinner("Đang xử lý..."):
                    try:
                        result = agent.invoke(
                            Command(resume={"decisions": decisions}),
                            config=config, version="v2",
                        )
                        resp = _extract_final_response(result)
                        if resp:
                            st.session_state.messages.append({"role": "assistant", "content": resp})
                    except Exception as e:
                        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Lỗi: {e}"})
                st.session_state.pending_interrupt = None
                st.rerun()


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _unwrap(value):
    """Unwrap LangGraph Overwrite/AddableValuesDict objects to plain values."""
    # Overwrite object — có attribute .value chứa giá trị thực
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return value.value
    return value


def _safe_messages(data) -> list:
    """Trích xuất danh sách messages an toàn từ data dict.

    Xử lý trường hợp data["messages"] là:
      - list bình thường
      - Overwrite(list)
      - một message đơn
      - None / không tồn tại
    """
    if not isinstance(data, dict):
        return []

    raw = data.get("messages")
    if raw is None:
        return []

    # Unwrap Overwrite
    raw = _unwrap(raw)

    if isinstance(raw, list):
        return raw
    # Nếu là một message đơn (có attribute .content)
    if hasattr(raw, "content"):
        return [raw]
    return []


def _extract_final_response(result) -> str:
    """Trích xuất text phản hồi cuối từ invoke result."""
    try:
        if hasattr(result, "value"):
            result = result.value
        if isinstance(result, dict):
            messages = _safe_messages(result)
            if messages:
                last = messages[-1]
                return last.content if hasattr(last, "content") else str(last)
    except Exception:
        pass
    return ""


def _identify_agent(ns) -> str:
    """Xác định tên agent đang hoạt động từ namespace tuple."""
    if not ns:
        return "🧠 Main Agent"
    ns_str = ":".join(str(s) for s in ns) if ns else ""
    for agent_key, display_name in SUBAGENT_DISPLAY.items():
        if agent_key in ns_str:
            return display_name
    return f"🤖 Sub-agent ({ns_str})"


def _describe_step(node_name: str, data, agent_label: str) -> str:
    """Tạo mô tả chi tiết cho mỗi bước streaming."""
    messages = _safe_messages(data)

    for msg in messages:
        try:
            # Tool call request (AI gọi tool)
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                # tool_calls cũng có thể là Overwrite
                tool_calls = _unwrap(tool_calls)
                if isinstance(tool_calls, list):
                    names = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            name = tc.get("name", tc.get("function", {}).get("name", "?"))
                        else:
                            name = getattr(tc, "name", "?")
                        names.append(f"`{name}`")
                    if names:
                        return f"⚙️ {agent_label} → Gọi tool: {', '.join(names)}"

            # Tool response
            msg_type = getattr(msg, "type", None)
            if msg_type == "tool":
                tool_name = getattr(msg, "name", "tool")
                return f"📨 {agent_label} → Nhận kết quả từ `{tool_name}`"

            # AI message (phản hồi cuối)
            if msg_type == "ai" and getattr(msg, "content", ""):
                if not getattr(msg, "tool_calls", None):
                    return f"💬 {agent_label} → Đang phản hồi..."
        except Exception:
            continue

    return f"⚙️ {agent_label} → **{node_name}**"


# ═══════════════════════════════════════════════════════════════
# CHAT INPUT + STREAMING
# ═══════════════════════════════════════════════════════════════

if prompt := st.chat_input("VD: Đặt lịch họp dự án chiều mai. Xem lịch hôm nay."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        inputs = {
            "messages": [("user", prompt)],
            "files": seed_files,
        }

        with st.status("AI đang xử lý...", expanded=True) as status:
            try:
                for chunk in agent.stream(
                    inputs, config=config,
                    stream_mode="updates", subgraphs=True, version="v2",
                ):
                    chunk_type = chunk.get("type", "")

                    if chunk_type == "updates":
                        ns = chunk.get("ns", ())
                        agent_label = _identify_agent(ns)
                        chunk_data = chunk.get("data", {})

                        # chunk_data có thể là dict hoặc Overwrite
                        chunk_data = _unwrap(chunk_data)
                        if not isinstance(chunk_data, dict):
                            continue

                        for node_name, node_data in chunk_data.items():
                            # node_data cũng có thể là Overwrite
                            node_data = _unwrap(node_data)

                            # Hiển thị mô tả chi tiết
                            step_desc = _describe_step(node_name, node_data, agent_label)
                            st.write(step_desc)

                            # Trích xuất response text
                            messages = _safe_messages(node_data)
                            for msg in messages:
                                try:
                                    if (hasattr(msg, 'content') and msg.content
                                            and getattr(msg, 'type', None) == 'ai'
                                            and not getattr(msg, 'tool_calls', None)):
                                        full_response = msg.content
                                except Exception:
                                    continue

                    elif chunk_type == "interrupts":
                        interrupt_value = chunk.get("data")
                        interrupt_value = _unwrap(interrupt_value)

                        if isinstance(interrupt_value, list) and interrupt_value:
                            interrupt_info = interrupt_value[0]
                            interrupt_info = _unwrap(interrupt_info)
                            if hasattr(interrupt_info, "value"):
                                interrupt_info = interrupt_info.value
                            st.session_state.pending_interrupt = interrupt_info
                            st.write("⏸️ **Chờ xác nhận từ người dùng...**")

                if st.session_state.pending_interrupt is None:
                    status.update(label="Đã hoàn tất!", state="complete", expanded=False)
                else:
                    status.update(label="⏸️ Chờ xác nhận", state="running", expanded=False)

            except Exception as e:
                st.error(f"Hệ thống gặp sự cố: {e}")
                status.update(label="Lỗi xử lý", state="error", expanded=False)

        if full_response:
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        if st.session_state.pending_interrupt is not None:
            st.rerun()