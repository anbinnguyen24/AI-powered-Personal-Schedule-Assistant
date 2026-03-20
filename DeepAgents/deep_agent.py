import os
import uuid
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional
from xml.parsers.expat import model

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from deepagents import create_deep_agent
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("Chưa tìm thấy HF_TOKEN trong file .env!")

DB_FILE = os.path.join(os.path.dirname(__file__), "..", "backend", "personal_schedule.db")

NOW = datetime.now()
CURRENT_TIME_STR = NOW.strftime("%A, ngày %d tháng %m năm %Y, lúc %H:%M")


# ═════════════════════════════════════════════════════════════
# SECTION 1: ĐỊNH NGHĨA TOOLS
# ═════════════════════════════════════════════════════════════

@tool
def get_personal_preferences(user_id: str = "default") -> str:
    """Truy xuất hồ sơ cá nhân, sở thích và thói quen của người dùng.
    Dùng tool này để hiểu bối cảnh cá nhân trước khi lập lịch.
    """
    # --- DỮ LIỆU MẪU CHO DEMO ---
    profiles = {
        "default": {
            "name": "Nael",
            "timezone": "Asia/Ho_Chi_Minh",
            "role": "Sinh viên CNTT",
            "habits": {
                "wake_up": "06:30",
                "sleep": "23:00",
                "study_peak": "08:00-11:00 và 19:00-22:00",
                "exercise": "17:00-18:00 (thứ 2, 4, 6)",
                "lunch": "11:30-13:00",
                "dinner": "18:00-19:00"
            },
            "preferences": {
                "study_session_max": "2 tiếng liên tục, nghỉ 15 phút",
                "meeting_preference": "Online qua Google Meet",
                "priority": "Ưu tiên học bài và làm đồ án",
                "avoid": "Không xếp lịch trước 7h sáng và sau 22h tối"
            },
            "courses": [
                "Trí tuệ nhân tạo (AI)",
                "Xử lý ngôn ngữ tự nhiên (NLP)",
                "Đồ án chuyên ngành"
            ]
        }
    }
    profile = profiles.get(user_id, profiles["default"])
    return json.dumps(profile, ensure_ascii=False, indent=2)


@tool
def check_calendar(date: str, time_range: str = "07:00-22:00") -> str:
    """Kiểm tra lịch học, lịch thi và các sự kiện hiện có trong ngày.
    Trả về danh sách sự kiện và các khoảng thời gian trống.

    Args:
        date: Ngày cần kiểm tra, định dạng YYYY-MM-DD
        time_range: Khoảng thời gian cần kiểm tra, VD: "07:00-22:00"
    """
    # --- DỮ LIỆU MẪU CHO DEMO ---
    sample_events = {
        "2026-03-20": [
            {"event": "Học Trí tuệ nhân tạo", "start": "07:30", "end": "09:30", "location": "Phòng A301"},
            {"event": "Họp nhóm đồ án", "start": "10:00", "end": "11:30", "location": "Thư viện"},
            {"event": "Đi tập Gym", "start": "17:00", "end": "18:00", "location": "Phòng Gym"},
        ],
        "2026-03-21": [
            {"event": "Học NLP", "start": "08:00", "end": "10:00", "location": "Phòng B201"},
            {"event": "Thi giữa kỳ AI", "start": "13:30", "end": "15:30", "location": "Hội trường A"},
        ],
        "2026-03-22": [
            {"event": "Seminar Machine Learning", "start": "09:00", "end": "11:00", "location": "Online"},
        ],
    }

    events = sample_events.get(date, [])

    # Tính toán khoảng trống
    try:
        start_h, start_m = map(int, time_range.split("-")[0].split(":"))
        end_h, end_m = map(int, time_range.split("-")[1].split(":"))
    except (ValueError, IndexError):
        start_h, start_m = 7, 0
        end_h, end_m = 22, 0

    free_slots = []
    sorted_events = sorted(events, key=lambda e: e["start"])
    current_time = f"{start_h:02d}:{start_m:02d}"
    range_end = f"{end_h:02d}:{end_m:02d}"

    for evt in sorted_events:
        if current_time < evt["start"]:
            free_slots.append({"start": current_time, "end": evt["start"]})
        current_time = max(current_time, evt["end"])

    if current_time < range_end:
        free_slots.append({"start": current_time, "end": range_end})

    result = {
        "date": date,
        "existing_events": events,
        "free_slots": free_slots,
        "total_events": len(events),
        "total_free_slots": len(free_slots)
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def search_knowledge_base(query: str) -> str:
    """Tìm kiếm thông tin từ tài liệu PDF/Docx trong cơ sở tri thức (Vector Database).
    Dùng tool này để tra cứu quy chế, tài liệu hướng dẫn, hoặc thông tin tham khảo.

    Args:
        query: Câu hỏi hoặc chủ đề cần tìm kiếm
    """
    DB_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

    try:

        if not os.path.exists(DB_DIR):
            return f"[RAG] Chưa có Vector Database tại {DB_DIR}. Hãy chạy rag_pipeline.py trước để nạp tài liệu."

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
        docs = vectorstore.similarity_search(query, k=3)

        if not docs:
            return f"[RAG] Không tìm thấy thông tin liên quan đến: '{query}'"

        result = "\n\n".join([
            f"📄 Trích xuất {i+1}:\n{doc.page_content}"
            for i, doc in enumerate(docs)
        ])
        return f"[RAG] Dữ liệu tìm được từ tài liệu:\n{result}"

    except ImportError:
        return "[RAG] Thiếu thư viện (langchain_huggingface hoặc langchain_chroma). Cài đặt trước khi dùng."
    except Exception as e:
        return f"[RAG] Lỗi khi truy xuất: {str(e)}"


@tool
def save_schedule(
    event_name: str,
    start_time: str,
    end_time: str = "",
    location: str = ""
) -> str:
    """Lưu một sự kiện mới vào hệ thống lịch trình cá nhân.
    ⚠️ Tool này sẽ yêu cầu xác nhận từ người dùng trước khi thực hiện.

    Args:
        event_name: Tên sự kiện cần tạo
        start_time: Thời gian bắt đầu (VD: "2026-03-21 14:00")
        end_time: Thời gian kết thúc (VD: "2026-03-21 15:30")
        location: Địa điểm (VD: "Phòng họp A301")
    """
    try:
        db_path = os.path.abspath(DB_FILE)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                created_at TEXT
            )''')
            conn.execute(
                "INSERT INTO schedules (event_name, start_time, end_time, location, created_at) VALUES (?, ?, ?, ?, ?)",
                (event_name, start_time, end_time, location, datetime.now().isoformat())
            )
            conn.commit()

        return (
            f"✅ ĐÃ LƯU THÀNH CÔNG!\n"
            f"  📌 Sự kiện: {event_name}\n"
            f"  🕐 Thời gian: {start_time} → {end_time}\n"
            f"  📍 Địa điểm: {location or 'Chưa xác định'}"
        )
    except Exception as e:
        return f"❌ Lỗi khi lưu lịch: {str(e)}"


# ═════════════════════════════════════════════════════════════
# SECTION 2: ĐỊNH NGHĨA SUB-AGENTS
# ═════════════════════════════════════════════════════════════

# Sub-agent A: Personal Preference Agent
preference_subagent = {
    "name": "preference-agent",
    "description": (
        "Truy xuất hồ sơ cá nhân và thói quen của người dùng. "
        "Dùng agent này khi cần biết sở thích, thời gian rảnh thường ngày, "
        "hoặc giới hạn cá nhân để lập lịch phù hợp."
    ),
    "system_prompt": """Bạn là chuyên gia phân tích hồ sơ cá nhân.
        NHIỆM VỤ:
        1. Sử dụng tool get_personal_preferences để lấy thông tin người dùng.
        2. Phân tích và tóm tắt các thói quen, sở thích, và giới hạn thời gian.
        3. Trả về kết quả có cấu trúc rõ ràng để hỗ trợ việc lập lịch.
        Luôn trả lời bằng tiếng Việt.""",
    "tools": [get_personal_preferences],
}

# Sub-agent B: Calendar Agent
calendar_subagent = {
    "name": "calendar-agent",
    "description": (
        "Kiểm tra lịch học, lịch thi và thời gian trống của người dùng. "
        "Dùng agent này khi cần biết ngày/giờ nào đang bận hoặc rảnh."
    ),
    "system_prompt": f"""Bạn là chuyên gia quản lý lịch trình.
        Thời gian hiện tại: {CURRENT_TIME_STR}
        NHIỆM VỤ:
        1. Sử dụng tool check_calendar để kiểm tra lịch của ngày cần xem.
        2. Xác định các khoảng thời gian trống phù hợp.
        3. Liệt kê rõ ràng: sự kiện đã có, slot trống, và đề xuất giờ tốt nhất.
        Luôn trả lời bằng tiếng Việt.""",
    "tools": [check_calendar],
}

# Sub-agent C: RAG Agent
rag_subagent = {
    "name": "rag-agent",
    "description": (
        "Tìm kiếm thông tin từ tài liệu PDF và cơ sở tri thức nội bộ. "
        "Dùng agent này khi cần tra cứu quy chế, nội quy, hoặc tài liệu tham khảo."
    ),
    "system_prompt": """Bạn là chuyên gia tra cứu tài liệu.
        NHIỆM VỤ:
        1. Sử dụng tool search_knowledge_base để tìm thông tin từ cơ sở tri thức.
        2. Trích xuất các thông tin quan trọng liên quan đến yêu cầu.
        3. Tóm tắt kết quả một cách ngắn gọn và hữu ích.
        Luôn trả lời bằng tiếng Việt.""",
    "tools": [search_knowledge_base],
}


# ═════════════════════════════════════════════════════════════
# SECTION 3: TẠO MAIN DEEP AGENT (Schedule Advisor)
# ═════════════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""Bạn là "Schedule Advisor" — Trợ lý AI thông minh chuyên tối ưu lịch trình cá nhân.

⏰ Thời gian hiện tại: {CURRENT_TIME_STR}

🎯 VAI TRÒ: Bạn là NGƯỜI ĐIỀU PHỐI CHÍNH (Main Agent) trong hệ thống multi-agent.
Bạn sẽ phân tích yêu cầu người dùng, sau đó phối hợp các sub-agent chuyên biệt để thu thập dữ liệu,
rồi tổng hợp và đưa ra đề xuất lịch trình tối ưu.

📋 QUY TRÌNH LÀM VIỆC (LUÔN tuân thủ thứ tự):

Bước 1 - PHÂN TÍCH YÊU CẦU:
  → Phân tích ý định (tạo lịch, hỏi thông tin, tối ưu, v.v.)
  → Trích xuất thực thể: ngày, giờ, sự kiện, địa điểm

Bước 2 - THU THẬP DỮ LIỆU (Dùng sub-agents):
  → preference-agent: Lấy sở thích và thói quen cá nhân
  → calendar-agent: Kiểm tra lịch trống và sự kiện hiện có
  → rag-agent: Tra cứu tài liệu nếu cần (quy chế, tài liệu hướng dẫn)

Bước 3 - SUY LUẬN & ĐỀ XUẤT:
  → Tổng hợp dữ liệu từ tất cả sub-agents
  → Phát hiện xung đột thời gian nếu có
  → Đề xuất lịch trình tối ưu, giải thích lý do

Bước 4 - LƯU LỊCH (chỉ khi người dùng đồng ý):
  → Sử dụng tool save_schedule để ghi lịch vào hệ thống
  → Tool này sẽ tự động dừng lại để chờ xác nhận từ người dùng (Human Review)

🚫 QUY TẮC:
- Luôn trả lời bằng tiếng Việt
- KHÔNG tự ý đổi giờ người dùng yêu cầu
- Giải thích rõ ràng lý do cho mỗi đề xuất
- Luôn hỏi xác nhận trước khi lưu lịch
- Nếu phát hiện xung đột, đề xuất giải pháp thay thế
"""


def create_schedule_advisor():
    """Khởi tạo Deep Agent chính với đầy đủ sub-agents và human-in-the-loop."""
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token: raise ValueError("Chưa tìm thấy HF_TOKEN trong file .env!")

    checkpointer = MemorySaver()

    agent = create_deep_agent(
        model=ChatOpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=hf_token,
            model="Qwen/Qwen2.5-72B-Instruct",
            temperature=0.2
        ),
    
        # System prompt cho Main Agent
        system_prompt=SYSTEM_PROMPT,

        # Tool trực tiếp trên Main Agent (save_schedule cần human approval)
        tools=[save_schedule],

        # 3 Sub-agents chuyên biệt
        subagents=[
            preference_subagent,
            calendar_subagent,
            rag_subagent,
        ],

        # Human-in-the-loop: Yêu cầu xác nhận trước khi lưu lịch
        interrupt_on={
            "save_schedule": True,  # Dừng lại để user approve/reject
        },

        # Checkpointer bắt buộc cho interrupt
        checkpointer=checkpointer,
    )

    return agent


# ═════════════════════════════════════════════════════════════
# SECTION 4: CLI RUNNER - CHẠY DEMO TƯƠNG TÁC
# ═════════════════════════════════════════════════════════════

def run_demo():
    """Chạy demo Deep Agent tương tác qua terminal."""
    print("=" * 65)
    print("  🤖 DEEP AGENT DEMO - AI Personal Schedule Assistant")
    print("  📅 Trợ lý lập lịch trình thông minh với Sub-agents")
    print(f"  ⏰ Thời gian hiện tại: {CURRENT_TIME_STR}")
    print("=" * 65)
    print()
    print("  Các khả năng cốt lõi:")
    print("    ✦ Sub-agents: Phân tích sở thích, kiểm tra lịch, RAG")
    print("    ✦ Human-in-the-loop: Xác nhận trước khi lưu lịch")
    print("    ✦ Schedule Advisor: Tổng hợp & đề xuất tối ưu")
    print()
    print("  Gõ 'quit' hoặc 'exit' để thoát.")
    print("-" * 65)

    # Khởi tạo agent
    print("\n⏳ Đang khởi tạo Deep Agent...")
    try:
        agent = create_schedule_advisor()
        print("✅ Deep Agent đã sẵn sàng!\n")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo: {e}")
        print("💡 Hãy kiểm tra HF_TOKEN và cài đặt: pip install deepagents")
        return

    # Tạo thread ID cho phiên làm việc
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"🔗 Thread ID: {thread_id[:8]}...\n")

    while True:
        # ── Lấy input từ người dùng ──
        try:
            user_input = input("👤 Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Tạm biệt!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "thoát"):
            print("\n👋 Tạm biệt! Hẹn gặp lại.")
            break

        print("\n🤖 Agent đang xử lý...")
        print("   (Đang phân tích → điều phối sub-agents → tổng hợp...)\n")

        try:
            # ── Gọi Agent ──
            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
                version="v2",
            )

            # ── Kiểm tra Human-in-the-loop Interrupt ──
            if hasattr(result, 'interrupts') and result.interrupts:
                interrupt_value = result.interrupts[0].value
                action_requests = interrupt_value.get("action_requests", [])
                review_configs = interrupt_value.get("review_configs", [])

                config_map = {cfg["action_name"]: cfg for cfg in review_configs}

                print("=" * 50)
                print("⏸️  HUMAN REVIEW - Xác nhận hành động")
                print("=" * 50)

                for action in action_requests:
                    tool_name = action.get("name", "unknown")
                    tool_args = action.get("args", {})
                    review_config = config_map.get(tool_name, {})

                    print(f"\n📋 Tool: {tool_name}")
                    print(f"📝 Tham số:")
                    for key, val in tool_args.items():
                        print(f"   • {key}: {val}")

                    allowed = review_config.get("allowed_decisions", ["approve", "reject"])
                    print(f"🔐 Quyết định cho phép: {', '.join(allowed)}")

                print("\n" + "-" * 50)
                user_decision = input("✋ Bạn có đồng ý lưu lịch trình? (y/n): ").strip().lower()

                if user_decision in ("y", "yes", "có", "đồng ý", "ok"):
                    decisions = [{"type": "approve"} for _ in action_requests]
                    print("\n✅ Đã xác nhận! Đang lưu lịch...\n")
                else:
                    decisions = [{"type": "reject"} for _ in action_requests]
                    print("\n❌ Đã từ chối. Lịch trình sẽ không được lưu.\n")

                # Resume agent với quyết định
                result = agent.invoke(
                    Command(resume={"decisions": decisions}),
                    config=config,
                    version="v2",
                )

            # ── Hiển thị kết quả cuối cùng ──
            if hasattr(result, 'value'):
                messages = result.value.get("messages", [])
            elif isinstance(result, dict):
                messages = result.get("messages", [])
            else:
                messages = []

            if messages:
                last_msg = messages[-1]
                content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
                print("─" * 50)
                print(f"🤖 Agent: {content}")
                print("─" * 50)
            else:
                print("🤖 Agent: (Không có phản hồi)")

        except Exception as e:
            print(f"\n⚠️ Lỗi khi xử lý: {e}")
            print("💡 Thử lại với yêu cầu khác.\n")

        print()


if __name__ == "__main__":
    run_demo()
