from src.agents.calendar_agent import calendar_subagent
from src.agents.research_agent import research_subagent
from src.agents.scheduling_agent import schedule_subagent

subagents = [
    research_subagent,
    calendar_subagent,
    schedule_subagent
]

supervisor = {
    "system_prompt": """Bạn là Supervisor của scheduling system.

    Workflow:
    1️. RESEARCH: User yêu cầu → research-agent
    2️. CALENDAR: Có research → calendar-agent  
    3️. SCHEDULE: Có availability → schedule-agent

    Luôn chọn đúng subagent và tổng hợp kết quả.
    Chỉ approve final schedule sau khi user confirm."""
}