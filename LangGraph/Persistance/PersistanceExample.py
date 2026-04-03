from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage

def assistant(state: MessagesState):
    # The assistant simply acknowledges the history
    return {"messages": [AIMessage(content="I have updated your profile in my memory.")]}

# 1. Initialize Memory Checkpointer
memory = MemorySaver()

# 2. Build and compile with checkpointer
workflow = StateGraph(MessagesState)
workflow.add_node("assistant", assistant)
workflow.add_edge(START, "assistant")
workflow.add_edge("assistant", END)

# Integrate the checkpointer during compilation
app = workflow.compile(checkpointer=memory)

# 3. Execution with Thread ID
config = {"configurable": {"thread_id": "session_123"}}

# First interaction
print("--- Round 1: Introduction ---")
app.invoke({"messages": [HumanMessage(content="Hi, I am an Engineer.")]}, config)

# Second interaction (The system remembers context via thread_id)
print("--- Round 2: Memory Check ---")
final_state = app.invoke({"messages": [HumanMessage(content="Do you remember my job?")]}, config)

for m in final_state["messages"]:
    m.pretty_print()