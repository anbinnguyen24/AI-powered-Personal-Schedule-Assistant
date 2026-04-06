from src.agents.calendar_agent import get_calendar_agent
from src.agents.research_agent import get_research_agent
from src.agents.supervisor import supervisor_node
from src.utils.llm_utils import create_chat_llm

# Khởi tạo LLM dùng chung
llm = create_chat_llm()

def call_supervisor_node(state):
    return supervisor_node(state, llm)

def call_calendar_node(state):
    agent = get_calendar_agent(llm)
    response = agent.invoke(state)
    new_messages = response["messages"][len(state["messages"]):]
    return {"messages": new_messages, "next": "FINISH"}

def call_research_node(state):
    agent = get_research_agent(llm)
    response = agent.invoke(state)
    new_messages = response["messages"][len(state["messages"]):]
    return {"messages": new_messages, "next": "FINISH"}