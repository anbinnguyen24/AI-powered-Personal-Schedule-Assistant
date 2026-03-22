import json
import os

from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from DeepAgents.agents.subagents import ALL_SUBAGENTS
from DeepAgents.backends import make_composite_backend, make_sandbox_backend
from DeepAgents.config.settings import ENABLE_SANDBOX, get_llm
from DeepAgents.prompts.main_agent import MAIN_AGENT_PROMPT
from DeepAgents.tools.preferences_tool import DEFAULT_PREFERENCES


# ═══════════════════════════════════════════════════════════════
# HELPER — Đọc nội dung file skill/memory vào dict seeding
# ═══════════════════════════════════════════════════════════════

_DEEPAGENTS_DIR = os.path.dirname(os.path.dirname(__file__))


def _load_local_file(relative_path: str) -> str:
    """Đọc file text từ thư mục DeepAgents."""
    abs_path = os.path.join(_DEEPAGENTS_DIR, relative_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_seed_files() -> dict:
    """Tạo dict files để seed vào StateBackend khi invoke.

    Bao gồm:
      - /skills/schedule-optimization/SKILL.md  (Capability: Skills)
      - /memories/AGENTS.md                     (Capability: Long-term Memory)
      - /memories/user_preferences.txt          (Default user preferences)
    """
    files = {}

    try:
        skill_content = _load_local_file(
            os.path.join("skills", "schedule-optimization", "SKILL.md")
        )
        files["/skills/schedule-optimization/SKILL.md"] = create_file_data(skill_content)
    except FileNotFoundError:
        pass

    try:
        memory_content = _load_local_file(os.path.join("memory", "AGENTS.md"))
        files["/memories/AGENTS.md"] = create_file_data(memory_content)
    except FileNotFoundError:
        pass

    # Seed default user preferences vào long-term memory
    prefs_content = json.dumps(DEFAULT_PREFERENCES, ensure_ascii=False, indent=2)
    files["/memories/user_preferences.txt"] = create_file_data(prefs_content)

    return files


# ═══════════════════════════════════════════════════════════════
# MAIN FUNCTION — Tạo Schedule Advisor Deep Agent
# ═══════════════════════════════════════════════════════════════

def create_schedule_advisor():
    """Khởi tạo Deep Agent chính với đầy đủ 8 core capabilities.

    Returns:
        tuple: (agent, seed_files)
          - agent: Compiled LangGraph agent
          - seed_files: dict files để seed vào virtual filesystem khi invoke
    """
    llm = get_llm()

    if ENABLE_SANDBOX:
        backend = make_sandbox_backend() or make_composite_backend
    else:
        backend = make_composite_backend

    store = InMemoryStore()
    checkpointer = MemorySaver()

    # Tạo Deep Agent
    agent = create_deep_agent(
        model=llm,
        system_prompt=MAIN_AGENT_PROMPT,
        tools=[],
        subagents=ALL_SUBAGENTS,
        backend=backend,
        store=store,
        skills=["/skills/"],
        memory=["/memories/AGENTS.md"],
        checkpointer=checkpointer,
    )

    return agent, _build_seed_files()
