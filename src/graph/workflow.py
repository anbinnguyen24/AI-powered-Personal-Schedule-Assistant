import os
import json
from datetime import datetime
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from src.graph.state import SchedulingState
from src.tools.google_calendar import calendar_tools
from src.tools.user_db import get_user_info
from src.tools.web_search import research_topic
from src.tools.rag_tool import consult_guidelines

load_dotenv()
def create_scheduling_workflow():
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token: raise ValueError("Chưa tìm thấy HF_TOKEN trong file .env!")

    model = ChatOpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=hf_token,
        model="Qwen/Qwen2.5-72B-Instruct",
        temperature=0.2
    )

    now = datetime.now()
    current_time_str = now.strftime("%A, ngày %d tháng %m năm %Y, %H:%M")

    # ==============================================================================================
    # 1. KHỞI TẠO CÁC SUB-AGENTS

    agent_1_rag = create_react_agent(model, tools=[consult_guidelines],
                                     prompt="Bạn là Agent 1. Nhiệm vụ: Tìm thông tin cá nhân, quy chế, sở thích từ tài liệu.")
    agent_2_web = create_react_agent(model, tools=[research_topic],
                                     prompt="Bạn là Agent 2. Nhiệm vụ: Lướt web tìm kiếm khóa học, địa điểm, tài liệu phù hợp với yêu cầu.")
    agent_3_cal = create_react_agent(model, tools=calendar_tools,
                                     prompt=f"Bạn là Agent 3. Thời gian: {current_time_str}. Kiểm tra lịch trống.")
    agent_4_creator = create_react_agent(model, tools=calendar_tools,
                                         prompt="Bạn là Agent 4. Tạo sự kiện lên Google Calendar.")

    # =========================================================================================================
    # 2. ĐỊNH NGHĨA CÁC NODES
    def router_node(state: SchedulingState):
        """Phân loại ý định của người dùng"""
        user_msg = state["messages"][-1].content

        # Nếu đang có bản nháp, có nghĩa user đang trả lời feedback
        if state.get("current_draft"):
            return {"intent": "feedback"}

        prompt = f"""Phân loại câu nói sau: "{user_msg}". 
        Chọn 1 trong các intent sau:
        - "greeting": Câu chào hỏi thông thường.
        - "off_topic": Câu hỏi không liên quan đến lập lịch trình, lộ trình học tập, đi chơi.
        - "schedule": Yêu cầu lên lịch trình sự kiện, đi chơi, họp hành (cần thời gian cụ thể).
        - "roadmap": Yêu cầu tư vấn lộ trình học tập, làm việc dài hạn (VD: Lộ trình học code).
        Trả về JSON: {{"intent": "tên_intent"}}"""

        response = model.invoke(prompt).content
        try:
            clean_json = response.strip().strip('`').removeprefix('json').strip()
            intent = json.loads(clean_json).get("intent", "schedule")
        except:
            intent = "schedule"  # Mặc định

        if intent == "greeting":
            msg = "Xin chào! Tôi là AI Trợ lý Cá nhân. Tôi có thể giúp bạn lập lịch trình đi chơi hoặc tư vấn lộ trình học tập chi tiết. Bạn cần tôi giúp gì hôm nay?"
            return {"intent": intent, "messages": [AIMessage(content=msg)]}
        elif intent == "off_topic":
            msg = "Xin lỗi, tôi là trợ lý chuyên về tối ưu lịch trình và tư vấn lộ trình cá nhân. Tôi không thể hỗ trợ các vấn đề ngoài lề này."
            return {"intent": intent, "messages": [AIMessage(content=msg)]}

        return {"intent": intent, "current_draft": ""}

    def info_checker_node(state: SchedulingState):
        """Kiểm tra xem yêu cầu đã đủ thông tin để làm chưa"""
        user_msg = state["messages"][-1].content
        intent = state.get("intent", "")
        missing_info = state.get("missing_info", [])

        # Nếu user đang bổ sung thông tin
        system_prompt = f"""Người dùng muốn {'Lập lộ trình' if intent == 'roadmap' else 'Lập lịch trình'}. 
        Yêu cầu của họ: "{user_msg}".
        Để làm được điều này một cách xuất sắc, hãy kiểm tra xem họ đã cung cấp đủ thông tin cốt lõi chưa?
        - Nếu là Lộ trình học: Cần biết Ngân sách, Trình độ hiện tại, Mục tiêu, Thời gian rảnh mỗi ngày.
        - Nếu là Lịch trình đi chơi: Cần biết Địa điểm mong muốn, Ngân sách, Đi cùng ai, Thời gian.

        Trả về JSON:
        {{
            "is_sufficient": true/false,
            "missing_fields": ["Danh sách các thông tin quan trọng còn thiếu"],
            "ask_user_message": "Câu hỏi lịch sự yêu cầu người dùng cung cấp thông tin hoặc upload file PDF/Docx nếu thiếu. Bỏ trống nếu đủ."
        }}"""

        response = model.invoke(system_prompt).content
        try:
            clean_json = response.strip().strip('`').removeprefix('json').strip()
            result = json.loads(clean_json)

            if not result["is_sufficient"]:
                return {
                    "missing_info": result["missing_fields"],
                    "messages": [AIMessage(content=result["ask_user_message"])]
                }
            return {"missing_info": []}  # Đã đủ thông tin
        except:
            return {"missing_info": []}  # Fallback cho đi tiếp

    def gather_info_node(state: SchedulingState):
        """Thu thập thông tin từ các Sub-Agents (Giữ nguyên logic của bạn, nâng cấp prompt)"""
        msg_input = {"messages": state["messages"]}
        intent = state.get("intent", "schedule")

        rag_res = agent_1_rag.invoke(msg_input)
        profile = rag_res["messages"][-1].content

        # Phân biệt tìm kiếm cho Roadmap hay Schedule
        web_task = "tìm kiếm các khóa học, tài liệu, chi phí" if intent == "roadmap" else "tìm kiếm địa điểm, nhà hàng"
        web_input = {"messages": [("user",
                                   f"Yêu cầu: {state['messages'][-1].content}. Sở thích từ PDF: {profile}. Hãy {web_task} phù hợp nhất. Nếu user chê nháp trước: {state.get('user_feedback', '')}, hãy đổi kết quả.")]}
        web_res = agent_2_web.invoke(web_input)
        research = web_res["messages"][-1].content

        cal_res = agent_3_cal.invoke(msg_input)
        slots = cal_res["messages"][-1].content

        return {"user_profile": profile, "research_data": research, "calendar_slots": slots}

    def supervisor_drafter_node(state: SchedulingState):
        """Suy luận và tạo bản nháp Lịch trình / Lộ trình"""
        user_msg = state["messages"][-1].content
        intent = state.get("intent", "schedule")
        feedback = state.get("user_feedback", "")
        old_draft = state.get("current_draft", "")

        type_str = "LỘ TRÌNH HỌC TẬP/PHÁT TRIỂN" if intent == "roadmap" else "LỊCH TRÌNH SỰ KIỆN"

        system_prompt = f"""Bạn là Chuyên gia Tư vấn kiêm Trưởng phòng Lập kế hoạch.
        - Thời gian hiện tại: {current_time_str}
        - Yêu cầu là: {type_str}
        - Profile/Ngữ cảnh (Từ file PDF user tải lên): {state.get('user_profile', '')}
        - Dữ liệu Research Web (Khóa học/Địa điểm): {state.get('research_data', '')}
        - Lịch trống hiện tại: {state.get('calendar_slots', '')}

        NHIỆM VỤ:
        1. Phân tích sâu sắc (VD: Ngân sách 5 triệu -> Đề xuất mua khóa học A 2 triệu trên Udemy, 3 triệu mua sách).
        2. TẠO BẢN NHÁP CHI TIẾT:
           - Với Lịch trình: Ghi rõ giờ giấc, địa điểm.
           - Với Lộ trình: Ghi rõ các giai đoạn, link tài liệu tham khảo, phân bổ thời gian trong tuần.
        3. NẾU LÀ SỬA ĐỔI: Khách vừa chê bản nháp cũ vì: "{feedback}". Hãy Xin lỗi, giải thích tại sao bản nháp MỚI này hợp lý hơn.
        4. KẾT THÚC CÂU: "Đây là bản nháp lộ trình/lịch trình, bạn có đồng ý chốt kế hoạch này không?"
        """

        response = model.invoke([("system", system_prompt), ("user", user_msg)])
        return {"current_draft": response.content, "messages": [response], "is_approved": False}

    def feedback_analyzer_node(state: SchedulingState):
        """Đánh giá feedback của user"""
        user_reply = state["messages"][-1].content
        prompt = f"""Khách hàng phản hồi về bản nháp: "{user_reply}".
        Khách hàng có ĐỒNG Ý chốt bản nháp này không? 
        Trả về JSON: {{"approved": true/false, "reason": "lý do nếu từ chối, để rỗng nếu đồng ý"}}"""

        response = model.invoke(prompt).content
        try:
            clean_json = response.strip().strip('`').removeprefix('json').strip()
            result = json.loads(clean_json)
            approved = result.get("approved", False)
            reason = result.get("reason", "")
        except:
            approved = any(word in user_reply.lower() for word in ['ok', 'chốt', 'đồng ý', 'tạo đi', 'duyệt', 'yes'])
            reason = user_reply if not approved else ""

        return {"is_approved": approved, "user_feedback": reason}

    def executor_node(state: SchedulingState):
        """Thực thi: Tạo Calendar hoặc Trả về Markdown Lộ trình"""
        intent = state.get("intent", "schedule")

        if intent == "roadmap":
            # Với lộ trình, thường không tạo 1 event calendar mà in ra full plan + kèm file/link
            final_msg = f"✅ Đã chốt lộ trình thành công! Dưới đây là lộ trình chính thức của bạn:\n\n{state['current_draft']}\n\n*Chúc bạn học tập và đạt mục tiêu tốt nhất!*"
            return {"messages": [AIMessage(content=final_msg)], "current_draft": ""}
        else:
            # Với lịch trình, tạo calendar
            input_msg = {"messages": [("user", f"Hãy chốt bản nháp này lên Google Calendar: {state['current_draft']}")]}
            res = agent_4_creator.invoke(input_msg)
            return {"messages": [AIMessage(content=f"✅ {res['messages'][-1].content}")], "current_draft": ""}

    # ==========================================
    # 3. ĐỊNH NGHĨA LUỒNG DI CHUYỂN (ROUTING)
    workflow = StateGraph(SchedulingState)

    workflow.add_node("router", router_node)
    workflow.add_node("info_checker", info_checker_node)
    workflow.add_node("gather_info", gather_info_node)
    workflow.add_node("supervisor", supervisor_drafter_node)
    workflow.add_node("feedback_analyzer", feedback_analyzer_node)
    workflow.add_node("executor", executor_node)

    # ĐIỀU HƯỚNG ROUTER
    def route_from_router(state: SchedulingState):
        intent = state.get("intent")
        if intent == "feedback": return "feedback_analyzer"
        if intent in ["greeting", "off_topic"]: return END
        return "info_checker"  # Nếu là schedule/roadmap -> Đi kiểm tra thông tin

    # ĐIỀU HƯỚNG INFO CHECKER
    def route_from_checker(state: SchedulingState):
        if len(state.get("missing_info", [])) > 0:
            return END  # Thiếu thông tin -> Dừng graph, trả tin nhắn về cho user (Ví dụ: "Bạn upload file PDF điểm cũ để tui xem nhé")
        return "gather_info"  # Đủ thông tin -> Đi thu thập data

    # ĐIỀU HƯỚNG FEEDBACK
    def route_feedback(state: SchedulingState):
        if state.get("is_approved"): return "executor"  # Đồng ý -> Tạo lịch/Xuất lộ trình
        return "gather_info"  # Từ chối -> Thu thập lại web/cal với feedback mới để làm nháp mới

    # KẾT NỐI
    workflow.add_edge(START, "router")
    workflow.add_conditional_edges("router", route_from_router)

    workflow.add_conditional_edges("info_checker", route_from_checker)
    workflow.add_edge("gather_info", "supervisor")
    workflow.add_edge("supervisor", END)  # Xong nháp -> Dừng lại (Human-in-the-loop) chờ user rep

    workflow.add_conditional_edges("feedback_analyzer", route_feedback)
    workflow.add_edge("executor", END)

    app = workflow.compile(checkpointer=MemorySaver())
    return app