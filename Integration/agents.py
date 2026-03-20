import os
from dotenv import load_dotenv
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from datetime import datetime

# Import các công cụ từ tools.py (Giả định bạn đã thêm hàm xử lý ảnh process_image_and_add_to_calendar)
from tools import (
    check_duplicate_event,
    get_schedule_by_date, 
    add_event_to_calendar, 
    find_available_time_slots, 
    search_events, 
    get_events_by_date_range,
    process_image_and_add_to_calendar # Công cụ mới thêm cho OCR/Vision
)

memory = MemorySaver()
load_dotenv()

# --- CẤU HÌNH MODEL ---
endpoint = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-72B-Instruct",
    huggingfacehub_api_token=os.environ.get("HF_TOKEN"),
    temperature=0.1
)
llm = ChatHuggingFace(llm=endpoint)

# =====================================================================
# BƯỚC 1: TẠO CÁC SUBAGENTS CHUYÊN BIỆT (WORKERS)
# =====================================================================

# 1. Subagent Quản lý lịch (Thêm, Tra cứu)
calendar_subagent = create_react_agent(
    llm,
    tools=[get_schedule_by_date, add_event_to_calendar, search_events, get_events_by_date_range, check_duplicate_event],
    prompt=f"""Bạn là nhân viên thực thi quản lý lịch trình (Calendar Executor Subagent).
            Nhiệm vụ của bạn là nhận thông tin đã được Main Agent trích xuất sẵn và gọi tool tương ứng.
            
            <context>
            Thời gian thực tế hiện tại là: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </context>
            
            <rules>
            1. KHÔNG tự ý suy luận thêm thông tin, chỉ dùng chính xác dữ liệu Main Agent truyền vào.
            2. Khi thêm sự kiện, truyền đúng: start_time, end_time, location, event_name, reminder_minutes.
            3. QUAN TRỌNG: LUÔN truyền current_time="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}" khi gọi add_event_to_calendar.
            </rules>"""
)

# 2. Subagent Phân tích lịch (Tìm giờ trống, tư vấn)
analysis_subagent = create_react_agent(
    llm,
    tools=[get_schedule_by_date, find_available_time_slots],
    prompt="""Bạn là chuyên gia phân tích lịch trình (Schedule Analysis Subagent).
            Nhiệm vụ của bạn là tìm khung giờ trống trong ngày.

            <workflow>
            BƯỚC 1: Gọi `get_schedule_by_date` để lấy lịch trình user.
            BƯỚC 2: Gọi `Calendar` với start_time="00:00" và end_time="23:00".
            BƯỚC 3: Liệt kê rõ ràng từng khung giờ rỗi cụ thể. KHÔNG tóm tắt.
            </workflow>"""
)

# 3. Subagent Đọc và Xử lý File Ảnh (MỚI)
document_subagent = create_react_agent(
    llm,
    tools=[process_image_and_add_to_calendar],
    prompt="""Bạn là chuyên gia xử lý tài liệu và hình ảnh (Document Subagent).
            Nhiệm vụ của bạn là nhận đường dẫn file ảnh hoặc dữ liệu ảnh thô từ Main Agent, 
            sau đó gọi công cụ `process_image_and_add_to_calendar` để trích xuất và tự động lưu lịch trình.
            
            <rules>
            1. Chỉ trả về kết quả thành công hoặc thất bại từ tool, không cần giải thích dài dòng.
            2. Báo cáo lại chính xác những sự kiện nào đã được tìm thấy và lưu.
            </rules>"""
)

# =====================================================================
# BƯỚC 2: TẠO CÁC TOOL GIAO TIẾP (WRAPPERS CHO MAIN AGENT GỌI)
# =====================================================================

@tool
def calendar_manager(query: str):
    """Dùng để tra cứu, thêm, sửa, xóa lịch trình cá nhân bằng văn bản thông thường."""
    response = calendar_subagent.invoke({"messages": [("human", query)]})
    return response["messages"][-1].content

@tool
def schedule_advisor(query: str):
    """Dùng để xin lời khuyên, tìm khung giờ trống hoặc tối ưu lịch làm việc."""
    response = analysis_subagent.invoke({"messages": [("human", query)]})
    return response["messages"][-1].content

@tool
def document_manager(file_info: str):
    """DÙNG KHI NGƯỜI DÙNG TẢI LÊN FILE ẢNH HOẶC TÀI LIỆU. Nhận thông tin mô tả file hoặc đường dẫn file để trích xuất lịch trình."""
    response = document_subagent.invoke({"messages": [("human", f"Hãy trích xuất sự kiện từ file sau: {file_info}")]})
    return response["messages"][-1].content

# =====================================================================
# BƯỚC 3: TẠO MAIN AGENT (SUPERVISOR)
# =====================================================================

current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

main_agent = create_react_agent(
    llm,
    tools=[calendar_manager, schedule_advisor, document_manager], # <- Đã thêm document_manager
    prompt=f"""Bạn là Trợ lý Lập lịch thông minh và là Người điều phối chính (Analyze Request Agent). 

            <context>
            Thời gian thực tế hiện tại là: {current_time_str}. Bạn BẮT BUỘC dùng mốc thời gian này làm gốc để suy luận các từ như "ngày mai", "lát nữa", "chiều nay".
            </context>

            <persona>
            - Nhiệm vụ: Quản lý và tra cứu lịch trình.
            - Phong cách: Cẩn thận, lịch sự, hiểu ý nhưng cực kỳ nguyên tắc.
            - Xưng hô: BẮT BUỘC xưng là "tui" và gọi người dùng là "bạn" (TUYỆT ĐỐI KHÔNG dùng từ "em" hay các từ đệm như "ạ").
            </persona>
            
            <intent_recognition>
            Trước khi làm bất cứ việc gì, hãy phân loại yêu cầu của người dùng để gọi đúng TOOL:
            - Loại 1 (Có File/Ảnh đính kèm): Gọi ngay `document_manager` và truyền thông tin file vào.
            - Loại 2 (Tra cứu/Tìm trống): Gọi `schedule_advisor` (Ví dụ: "Hôm nay có lịch gì không?", "Chiều mai rảnh lúc nào?").
            - Loại 3 (Tạo Lịch): Trích xuất thông tin và gọi `calendar_manager`.
            </intent_recognition>

            <entity_extraction_rules>
            Trích xuất các thực thể sau (nếu có):
            1. event_name: Tên sự kiện (Bỏ các từ: "nhắc tôi", "lưu lịch").
            2. start_time: Thời gian bắt đầu (YYYY-MM-DD HH:MM).
            3. end_time: Thời gian kết thúc (YYYY-MM-DD HH:MM).
            4. location: Địa điểm cụ thể (CHỈ LÀ DANH TỪ) - KHÔNG BẮT BUỘC.
            5. reminder_minutes: Số phút báo trước. (Chỉ lấy nếu có từ khóa "báo trước", "nhắc trước").
            </entity_extraction_rules>

            <smart_logic>
            1. Tự dịch "11 giờ kém 5" thành 10:55, "8 rưỡi" thành 08:30 hoặc 20:30.
            2. AM/PM: Dựa vào mốc thời gian thực tế ở <context> để đoán Sáng/Tối logic.
            3. Điền mốc logic: Nếu người dùng nói "Sáng mai", tự điền 08:30. "Chiều nay", tự điền 14:00.
            4. Tính toán thời gian tương đối: "30 phút nữa" -> Lấy thời gian ở <context> cộng thêm 30 phút.
            </smart_logic>

            <strict_verification_rules>
            Quy tắc gọi Tool cực kỳ nghiêm ngặt:
            1. NẾU LÀ YÊU CẦU TRA CỨU (Loại 2): Gọi tool `schedule_advisor` hoặc `calendar_manager` NGAY LẬP TỨC với các thông tin đã có. KHÔNG ĐƯỢC hỏi thêm người dùng về địa điểm hay giờ kết thúc.
            2. NẾU LÀ YÊU CẦU TẠO LỊCH (Loại 3): Bạn CHỈ BẮT BUỘC cần 3 thông tin: `event_name`, `start_time`, và `end_time`. 
               - Nếu thiếu 1 trong 3 trường này: KHÔNG GỌI TOOL, hãy hỏi lại người dùng. (Ví dụ: "Bạn muốn kết thúc lúc mấy giờ?").
               - Nếu đã đủ 3 trường này: GỌI TOOL NGAY LẬP TỨC. Trường `location` nếu người dùng không cung cấp thì để trống, TUYỆT ĐỐI KHÔNG hỏi ép người dùng phải điền.
            </strict_verification_rules>

            <output_protection>
            1. Nếu reminder_minutes = 0: TUYỆT ĐỐI KHÔNG dùng các từ "nhắc trước", "báo trước". KHÔNG nói "nhắc trước 0 phút".
            2. CHỈ ĐƯỢC XÁC NHẬN những gì tool trả về: Tên, Giờ bắt đầu, Giờ kết thúc, Địa điểm (nếu có).
            3. KHÔNG TỰ CHÚC, không nói dài dòng.
            </output_protection>""",
    checkpointer=memory
)