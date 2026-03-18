from langgraph.types import RetryPolicy
from langgraph.graph import StateGraph
import state

workflow = StateGraph(state.ScheduleAgentState)

# Khi thêm node vào workflow, ta cấu hình chính sách thử lại
workflow.add_node(
    "calendar_check",
    calendar_check,
    # Thử lại tối đa 3 lần, mỗi lần cách nhau tăng dần từ 1 giây
    retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0)
)

workflow.add_node(
    "rag_search",
    rag_search,
    retry_policy=RetryPolicy(max_attempts=2)
)