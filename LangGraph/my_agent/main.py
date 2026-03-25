# main.py
from my_agent.agent import build_app
from langchain_core.messages import HumanMessage
from langgraph.types import Command

app = build_app()
user_input = input("Nhập yêu cầu của bạn: ")

input_data = {
    "messages": [HumanMessage(content=user_input)],
    "is_approved": False
}
config = {"configurable": {"thread_id": "demo_001"}}

for _ in app.stream(input_data, config):
    pass

state = app.get_state(config)
if state.next and state.next[0] == "human_review":
    draft = state.values.get("proposed_schedule", {})
    draft_text = draft.get("content") or (
        f"{draft.get('event', 'Sự kiện')} lúc {draft.get('time', '--:--')} ngày {draft.get('date', '----/--/--')}"
    )
    print(f"Bản nháp: {draft_text}")
    user_choice = input("Bạn có đồng ý không? (y/n): ").strip().lower()
    app.invoke(Command(resume={"approved": user_choice=='y'}), config)

final_state = app.get_state(config)
if "messages" in final_state.values:
    print("=== PHẢN HỒI CUỐI CÙNG ===")
    print(final_state.values["messages"][-1].content)
print("=== KẾT THÚC ===")
