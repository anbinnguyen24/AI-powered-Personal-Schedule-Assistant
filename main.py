from agents import main_agent

config = {"configurable": {"thread_id": "user_123"}}

def chat():
    print("--- Trợ lý đã sẵn sàng---")
    while True:
        user_input = input("Bạn: ")
        if user_input.lower() in ["exit", "quit"]: break

        inputs = {"messages": [("human", user_input)]}

        # 1. Truyền config vào hàm stream
        for output in main_agent.stream(inputs, config=config, stream_mode="updates"):
            for node, value in output.items():
                print(f"[{node}]: {value['messages'][-1].content}")

        state = main_agent.get_state(config)
        print(f"Trạng thái hiện tại của luồng {config['configurable']['thread_id']} đã được lưu.")


if __name__ == "__main__":
    chat()