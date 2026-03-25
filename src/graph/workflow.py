from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from src.graph.state import AgentState
from src.agents.supervisor import supervisor_node
from src.tools.google_calendar import get_calendar_tools
from src.tools.web_search import web_search_tool
from src.tools.rag_tool import consult_guidelines
from src.tools.user_db import get_user_info
from langchain_openai import ChatOpenAI
import os

load_dotenv()
hf_token = os.environ.get("HF_TOKEN")
llm = ChatOpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=hf_token,
        model="Qwen/Qwen2.5-72B-Instruct",
        temperature=0.2
    )

# Khởi tạo Agents
calendar_agent = create_react_agent(llm, tools=get_calendar_tools() + [get_user_info])
research_agent = create_react_agent(llm, tools=[web_search_tool, consult_guidelines])

def calendar_node(state: AgentState):
    print("📅 [Calendar] Đang chạy...")
    result = calendar_agent.invoke({"messages": state["messages"]})
    return {"messages": [result["messages"][-1]]}

def research_node(state: AgentState):
    print("🔍 [Research] Đang chạy...")
    result = research_agent.invoke({"messages": state["messages"]})
    return {"messages": [result["messages"][-1]]}

# Lắp ráp Workflow
workflow = StateGraph(AgentState)
workflow.add_node("Supervisor", lambda state: supervisor_node(state, llm))
workflow.add_node("CalendarAgent", calendar_node)
workflow.add_node("ResearchAgent", research_node)

workflow.set_entry_point("Supervisor")

# Điều kiện rẽ nhánh (Chặn lặp vô hạn nhờ nút FINISH)
workflow.add_conditional_edges(
    "Supervisor",
    lambda state: state["next"],
    {
        "CalendarAgent": "CalendarAgent",
        "ResearchAgent": "ResearchAgent",
        "FINISH": END
    }
)

# Làm xong thì quay lại Supervisor báo cáo
workflow.add_edge("CalendarAgent", "Supervisor")
workflow.add_edge("ResearchAgent", "Supervisor")

app = workflow.compile(checkpointer=MemorySaver())