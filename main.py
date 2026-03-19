# from subagents import main_agent
#
# config = {"configurable": {"thread_id": "user_123"}}
#
# def chat():
#     print("--- Trợ lý đã sẵn sàng---")
#     while True:
#         user_input = input("Bạn: ")
#         if user_input.lower() in ["exit", "quit"]: break
#
#         inputs = {"messages": [("human", user_input)]}
#
#         # 1. Truyền config vào hàm stream
#         for output in main_agent.stream(inputs, config=config, stream_mode="updates"):
#             for node, value in output.items():
#                 print(f"[{node}]: {value['messages'][-1].content}")
#
#         state = main_agent.get_state(config)
#         print(f"Trạng thái hiện tại của luồng {config['configurable']['thread_id']} đã được lưu.")
#
#
# if __name__ == "__main__":
#     chat()


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