from dotenv import load_dotenv
from src.graph.workflow import create_scheduling_workflow

load_dotenv()
graph = create_scheduling_workflow()

# Interrupt cho human approval
config = {"configurable": {
    "thread_id": "user_123",
    "checkpoint_id": None  # Durable execution
}}

# Step 1: Research & Calendar
input1 = {
    "messages": [{"role": "user", "content": "Lên lịch meeting Q1 roadmap"}],
    "user_id": "user123"
}

for chunk in graph.stream(input1, config, stream_mode="values"):
    print(chunk["messages"][-1].content)

# Human approve (manual hoặc UI)
config["configurable"]["human_approved"] = True

# Step 2: Create event
input2 = {"messages": [{"role": "user", "content": "OK, approve 10AM"}]}
graph.invoke(input2, config)