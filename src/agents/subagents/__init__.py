from src.agents.subagents.preference_agent import preference_subagent
from src.agents.subagents.calendar_agent import calendar_subagent
from src.agents.subagents.rag_agent import rag_subagent


ALL_SUBAGENTS = [preference_subagent, calendar_subagent, rag_subagent]

__all__ = [
    "preference_subagent",
    "calendar_subagent",
    "rag_subagent",
    "ALL_SUBAGENTS",
]
