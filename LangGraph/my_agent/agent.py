# agent.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import RetryPolicy
from .utils.state import ScheduleAgentState
from .utils.nodes import analyze_request, calendar_check, schedule_advisor, human_review, update_save_response

# Build workflow
workflow = StateGraph(ScheduleAgentState)

workflow.add_node("analyze_request", analyze_request)
workflow.add_node("calendar_check", calendar_check, retry_policy=RetryPolicy(max_attempts=3))
workflow.add_node("schedule_advisor", schedule_advisor)
workflow.add_node("human_review", human_review)
workflow.add_node("update_save_response", update_save_response)

workflow.add_edge(START, "analyze_request")
workflow.add_edge("update_save_response", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

def build_app():
    return app