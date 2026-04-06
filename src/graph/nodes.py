import re
from datetime import datetime, timedelta, timezone
from typing import Any
from src.agents import calendar_agent, research_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from src.graph.state import AgentState
from src.agents.calendar_agent import get_calendar_agent
from src.agents.research_agent import get_research_agent
from src.agents.supervisor import supervisor_node
from src.utils.llm_utils import create_chat_llm


llm = create_chat_llm()
def call_supervisor_node(state):
    return supervisor_node(state, llm)

def call_calendar_node(state):
    agent = get_calendar_agent(llm)
    response = agent.invoke(state)
    return {"messages": response["messages"], "next": "FINISH"}

def call_research_node(state):
    agent = get_research_agent(llm)
    response = agent.invoke(state)
    return {"messages": response["messages"], "next": "FINISH"}