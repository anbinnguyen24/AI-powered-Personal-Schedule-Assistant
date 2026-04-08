import os
import json
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from src.graph.state import OuterAgentState
from src.graph.nodes import load_preference_node, get_execute_deep_agent_node
from src.agents.subagents import ALL_SUBAGENTS
from src.backends import make_composite_backend, make_sandbox_backend
from src.config.settings import ENABLE_SANDBOX, get_llm
from src.prompts.main_agent import MAIN_AGENT_PROMPT
from src.tools.preferences_tool import DEFAULT_PREFERENCES

# ═══════════════════════════════════════════════════════════════
# HELPER SEED FILES
# ═══════════════════════════════════════════════════════════════
_DEEPAGENTS_DIR = os.path.dirname(os.path.dirname(__file__))


def _load_local_file(relative_path: str) -> str:
    abs_path = os.path.join(_DEEPAGENTS_DIR, relative_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_seed_files() -> dict:
    files = {}
    try:
        skill_content = _load_local_file(os.path.join("skills", "schedule-optimization", "SKILL.md"))
        files["/skills/schedule-optimization/SKILL.md"] = create_file_data(skill_content)
    except FileNotFoundError:
        pass
    try:
        memory_content = _load_local_file(os.path.join("memory", "AGENTS.md"))
        files["/memories/AGENTS.md"] = create_file_data(memory_content)
    except FileNotFoundError:
        pass

    prefs_content = json.dumps(DEFAULT_PREFERENCES, ensure_ascii=False, indent=2)
    files["/memories/user_preferences.txt"] = create_file_data(prefs_content)
    return files


# ═══════════════════════════════════════════════════════════════
# BUILDER FUNCTION
# ═══════════════════════════════════════════════════════════════
def create_hybrid_workflow():
    """Hàm khởi tạo và biên dịch toàn bộ Graph."""
    llm = get_llm()

    if ENABLE_SANDBOX:
        backend = make_sandbox_backend() or make_composite_backend
    else:
        backend = make_composite_backend

    # 1. Khởi tạo Store (Bộ nhớ dùng chung)
    store = InMemoryStore()

    # 2. Khởi tạo lõi DeepAgent
    deep_agent = create_deep_agent(
        model=llm,
        system_prompt=MAIN_AGENT_PROMPT,
        tools=[],
        subagents=ALL_SUBAGENTS,
        backend=backend,
        store=store,
        skills=["/skills/"],
        memory=["/memories/AGENTS.md"],
    )

    # 3. Vẽ luồng LangGraph
    workflow = StateGraph(OuterAgentState)

    workflow.add_node("load_preference", load_preference_node)
    workflow.add_node("deep_agent_core", get_execute_deep_agent_node(deep_agent))

    workflow.add_edge(START, "load_preference")
    workflow.add_edge("load_preference", "deep_agent_core")
    workflow.add_edge("deep_agent_core", END)

    # 4. Thiết lập Checkpointer và Store vòng ngoài
    outer_checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=outer_checkpointer, store=store)

    return app, _build_seed_files()