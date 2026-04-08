import json
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from src.tools.preferences_tool import DEFAULT_PREFERENCES
from src.graph.state import OuterAgentState


def load_preference_node(state: OuterAgentState):
    """Node ép buộc nạp hồ sơ người dùng vào SystemMessage trước khi xử lý."""
    has_preference = any(
        isinstance(msg, SystemMessage) and "[HỒ SƠ CÁ NHÂN NGƯỜI DÙNG]" in msg.content
        for msg in state["messages"]
    )

    if not has_preference:
        prefs = json.dumps(DEFAULT_PREFERENCES, ensure_ascii=False, indent=2)
        sys_msg = SystemMessage(
            content=f"[HỒ SƠ CÁ NHÂN NGƯỜI DÙNG]\n{prefs}\n(SOP: Luôn ưu tiên dùng thông tin này để tư vấn lịch trình)"
        )
        return {"messages": [sys_msg]}

    return {}


def get_execute_deep_agent_node(deep_agent):
    """Factory Pattern: Trả về hàm thực thi Node lồng ghép DeepAgent."""

    def execute_deep_agent_node(state: OuterAgentState, config: RunnableConfig):
        # Đồng bộ config (Store/ThreadID) từ LangGraph vòng ngoài vào DeepAgent vòng trong
        response = deep_agent.invoke({"messages": state["messages"]}, config=config)

        # Chỉ trả về những message mới do Agent sinh ra
        new_messages = response["messages"][len(state["messages"]):]
        return {"messages": new_messages}

    return execute_deep_agent_node