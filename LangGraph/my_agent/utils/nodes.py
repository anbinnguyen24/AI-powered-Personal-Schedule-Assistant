# nodes.py
from .tools import get_calendar_events, add_calendar_event, check_schedule_conflict, format_schedule
from .state import ScheduleAgentState, ScheduleIntent
from langgraph.types import Command, interrupt
from langgraph.graph import END
from langchain_core.messages import AIMessage
from langchain_ollama import ChatOllama
from typing import TypedDict

llm = ChatOllama(model="llama3.1")


class ProposedEvent(TypedDict):
    event: str
    time: str
    date: str

# --- Node 1: Phân tích yêu cầu ---
def analyze_request(state: ScheduleAgentState):
    user_msg = state["messages"][-1].content
    structured_intent_llm = llm.with_structured_output(ScheduleIntent)
    intent_result = structured_intent_llm.invoke(
        f"Phân tích yêu cầu sau để quản lý lịch trình: {user_msg}"
    )

    # Trích xuất lịch hoàn toàn bằng LLM.
    structured_schedule_llm = llm.with_structured_output(ProposedEvent)
    parsed_result = structured_schedule_llm.invoke(
        f"""
Trích xuất lịch từ câu sau và trả về JSON với đúng các trường event, time, date.
- event: tên sự kiện ngắn gọn
- time: HH:MM (24h)
- date: YYYY-MM-DD (nếu người dùng nói 'sáng mai', hiểu là ngày mai)

Câu người dùng: {user_msg}
"""
    )
    extracted_schedule = {
        "event": parsed_result["event"],
        "time": parsed_result["time"],
        "date": parsed_result["date"],
        "content": user_msg,
    }
    print(f"DEBUG: Phân tích yêu cầu, intent: {intent_result}, lịch trích xuất: {extracted_schedule}")

    return Command(
        update={
            "classification": intent_result,
            "proposed_schedule": extracted_schedule,
            "requested_schedule": extracted_schedule,
            "review_attempts": 0,
            "is_approved": False,
        },
        goto="calendar_check",
    )

# --- Node 2: Lấy lịch hiện tại ---
def calendar_check(state: ScheduleAgentState):
    user_id = "demo_user"
    events = get_calendar_events(user_id)

    return Command(update={"calendar_data": events}, goto="schedule_advisor")

# --- Node 3: Tư vấn lịch ---
def schedule_advisor(state: ScheduleAgentState):
    intent = state["classification"]
    calendar = state.get("calendar_data", [])
    requested_event = state.get("requested_schedule") or state.get("proposed_schedule")
    new_event = requested_event
    initial_conflict = None
    review_attempts = state.get("review_attempts", 0)

    # Chỉ ưu tiên lịch người dùng nhập ở lần đề xuất đầu tiên.
    if review_attempts == 0 and new_event and new_event.get("date") and new_event.get("time"):
        initial_conflict = check_schedule_conflict(new_event, calendar)
        if not initial_conflict:
            return Command(update={"proposed_schedule": new_event}, goto="human_review")

    # Giữ lại context lịch người dùng nhập để LLM hiểu rõ hơn.
    user_schedule_hint = ""
    if new_event and "content" in new_event:
        user_schedule_hint = new_event.get("content", "")

    rejected_note = ""
    previous_proposal = state.get("proposed_schedule")
    if review_attempts > 0 and isinstance(previous_proposal, dict):
        rejected_note = (
            f"Người dùng vừa từ chối lịch: {previous_proposal.get('event', 'Sự kiện')} lúc "
            f"{previous_proposal.get('time', '--:--')} ngày {previous_proposal.get('date', '----/--/--')}. "
            "Hãy đề xuất lịch khác rõ ràng so với lịch vừa bị từ chối."
        )

    structured_llm = llm.with_structured_output(ProposedEvent)
    conflict_note = ""
    candidate = None

    # Thử tối đa 3 lần để tạo một lịch không trùng.
    for _ in range(3):
        prompt = f"""
Người dùng muốn: {intent['action']} cho việc {intent['entities']}.
Lịch hiện tại: {calendar}
Gợi ý thêm từ người dùng: {user_schedule_hint}
{rejected_note}
{conflict_note}

Hãy đề xuất 1 lịch mới KHÔNG bị trùng.
Trả về JSON gồm:
- event: tên sự kiện
- time: giờ (HH:MM)
- date: ngày (YYYY-MM-DD)
"""

        result = structured_llm.invoke(prompt)
        preferred_event_name = new_event.get("event") if isinstance(new_event, dict) else None
        candidate = {
            "event": preferred_event_name or result["event"],
            "time": result["time"],
            "date": result["date"],
            "content": f"{preferred_event_name or result['event']} lúc {result['time']} ngày {result['date']}",
        }

        conflict = check_schedule_conflict(candidate, calendar)
        if not conflict:
            if initial_conflict and new_event:
                requested_text = (
                    f"{new_event.get('event', 'Sự kiện')} lúc {new_event.get('time', '--:--')} "
                    f"ngày {new_event.get('date', '----/--/--')}"
                )
                candidate_text = (
                    f"{candidate.get('event', 'Sự kiện')} lúc {candidate.get('time', '--:--')} "
                    f"ngày {candidate.get('date', '----/--/--')}"
                )
                candidate["content"] = (
                    f"Lịch bạn chọn ({requested_text}) bị trùng với "
                    f"{initial_conflict.get('event', 'sự kiện khác')} lúc "
                    f"{initial_conflict.get('time', '--:--')} ngày "
                    f"{initial_conflict.get('date', '----/--/--')}. "
                    f"Gợi ý lịch mới: {candidate_text}. Bạn có đồng ý đổi sang lịch này không?"
                )
            return Command(update={"proposed_schedule": candidate}, goto="human_review")

        conflict_note = (
            f"Lịch vừa đề xuất bị trùng với sự kiện: {conflict}. "
            "Hãy chọn thời điểm khác."
        )

    return Command(
        update={
            "proposed_schedule": {
                "content": "Không tìm được khung giờ phù hợp không trùng lịch. Vui lòng nhập thêm ràng buộc thời gian."
            }
        },
        goto="human_review",
    )

# --- Node 4: Human review ---
def human_review(state: ScheduleAgentState):
    draft = state.get("proposed_schedule", {})
    decision = interrupt({
        "info": "Tôi đã lập xong bản nháp lịch trình. Bạn có đồng ý cập nhật không?",
        "proposed_schedule": draft
    })
    if decision.get("approved") is True:
        return Command(update={"is_approved": True}, goto="update_save_response")

    attempts = state.get("review_attempts", 0) + 1
    if attempts < 3:
        return Command(
            update={
                "is_approved": False,
                "review_attempts": attempts,
                "messages": [
                    AIMessage(content=f"Bạn chưa đồng ý (lần {attempts}/3). Mình sẽ gợi ý một lịch khác.")
                ],
            },
            goto="schedule_advisor",
        )

    return Command(
        update={
            "is_approved": False,
            "review_attempts": attempts,
            "messages": [
                AIMessage(content="Bạn đã từ chối 3 lần. Mình dừng cập nhật lịch và giữ nguyên dữ liệu hiện tại.")
            ],
        },
        goto=END,
    )

# --- Node 5: Cập nhật lịch ---
def update_save_response(state: ScheduleAgentState):
    event_to_save = state["proposed_schedule"]
    user_id = "demo_user"
    msg = add_calendar_event(user_id, event_to_save)
    updated_events = get_calendar_events(user_id)
    schedule_text = format_schedule(updated_events)
    return {
        "messages": [
            AIMessage(
                content=f"Xong! {msg}\n\n=== TOÀN BỘ LỊCH TRÌNH ===\n{schedule_text}"
            )
        ]
    }