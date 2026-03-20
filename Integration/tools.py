import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
import io
import json
import pytesseract
from PIL import Image
from langchain_core.messages import HumanMessage

# Thiết lập đường dẫn lưu Vector DB vào thư mục backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
os.makedirs(BACKEND_DIR, exist_ok=True)

# Tải biến môi trường
load_dotenv()

# Khởi tạo mô hình Embedding qua Inference API
embeddings = HuggingFaceEndpoint(
    model="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
)

# Khởi tạo cơ sở dữ liệu Vector (ChromaDB) và chỉ định thư mục lưu trữ
vector_db = Chroma(
    collection_name="schedule_events",
    embedding_function=embeddings,
    persist_directory=BACKEND_DIR # Lưu dữ liệu offline trực tiếp vào folder backend
)

@tool
def get_schedule_by_date(date: str):
    """Lấy danh sách các sự kiện TRONG MỘT NGÀY CỤ THỂ.
    - date: chuỗi ngày theo định dạng YYYY-MM-DD.
    """
    # Lấy chính xác các document có metadata "date" khớp với ngày được yêu cầu
    results = vector_db.get(where={"date": date})
    
    if not results['documents']:
        return f"Bạn không có lịch trình nào vào ngày {date}."
    
    # In ra danh sách sự kiện
    events_str = "\n".join([f"- {doc}" for doc in results['documents']])
    return f"Lịch trình chính thức của bạn trong ngày {date}:\n{events_str}"

@tool
def search_events(query: str, k: int = 3):
    """Tìm kiếm sự kiện theo thông tin (tên, địa điểm) hoặc dự đoán các sự kiện có khả năng xảy ra.
    - query: Chuỗi tìm kiếm (Ví dụ: 'họp với khách hàng', 'các sự kiện ở quận 1').
    """
    # Tìm top k sự kiện có ý nghĩa tương đồng nhất với câu hỏi
    results = vector_db.similarity_search(query, k=k)
    
    if not results:
        return f"Không tìm thấy sự kiện nào liên quan hoặc có khả năng xảy ra với thông tin: '{query}'."
    
    events_str = "\n".join([f"- {doc.page_content}" for doc in results])
    return f"Dựa trên dữ liệu, đây là các sự kiện liên quan hoặc có khả năng xảy ra cao nhất:\n{events_str}"

@tool
def get_events_by_date_range(start_date: str, end_date: str):
    """Lấy danh sách sự kiện trong một KHOẢNG THỜI GIAN.
    - start_date: Ngày bắt đầu (YYYY-MM-DD).
    - end_date: Ngày kết thúc (YYYY-MM-DD).
    Ví dụ: Tìm sự kiện từ 2026-03-18 đến 2026-03-25.
    """
    results = vector_db.get(
        where={
            "$and": [
                {"date": {"$gte": start_date}},
                {"date": {"$lte": end_date}}
            ]
        }
    )
    
    if not results['documents']:
        return f"Không có sự kiện nào từ {start_date} đến {end_date}."
    
    events_str = "\n".join([f"- {doc}" for doc in results['documents']])
    return f"Các sự kiện từ {start_date} đến {end_date}:\n{events_str}"

@tool
def add_event_to_calendar(event_name: str, start_time: str, end_time: str, location: str = "", reminder_minutes: int = 0, current_time: str = ""):
    """Thêm một sự kiện mới vào lịch. (event_name, start_time, end_time là BẮT BUỘC)
    - event_name: tên hoặc nội dung sự kiện.
    - start_time: thời gian bắt đầu (YYYY-MM-DD HH:MM).
    - end_time: thời gian kết thúc (YYYY-MM-DD HH:MM).
    - location: địa điểm diễn ra sự kiện, có thể để trống.
    - reminder_minutes: số phút nhắc trước sự kiện (ví dụ: 30), mặc định là 0.
    - current_time: thời gian hiện tại để kiểm tra (nếu để trống sẽ lấy giờ hệ thống).
    """
    if not current_time:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Kiểm tra thời gian quá khứ
    is_valid_time, time_error = validate_event_time(start_time, current_time)
    if not is_valid_time:
        return f"❌ {time_error}"
    
    # Kiểm tra trùng lặp
    is_duplicate = check_duplicate_event(start_time, event_name)
    if is_duplicate:
        return f"⚠️ Sự kiện **{event_name}** lúc **{start_time}** đã có trong lịch. Không thêm sự kiện trùng."
    
    date_str = start_time[:10] 
    
    metadata = {
        "status": "scheduled",
        "date": date_str,
        "event_name": event_name,
        "start_time": start_time,
        "end_time": end_time,
        "location": location,
        "reminder_minutes": reminder_minutes
    }

    try:
        clean_start_time = start_time[:16] 
        dt = datetime.strptime(clean_start_time, "%Y-%m-%d %H:%M")
        reminder_dt = dt - timedelta(minutes=reminder_minutes)
        metadata["reminder_timestamp"] = int(reminder_dt.timestamp())
    except ValueError:
        pass 

    # Xây dựng câu văn miêu tả sự kiện dựa trên thông tin có sẵn
    text_content = f"Sự kiện: {event_name}. Bắt đầu lúc: {start_time}. Kết thúc lúc: {end_time}."
    if location:
        text_content += f" Địa điểm: {location}."

    vector_db.add_texts(
        texts=[text_content], 
        metadatas=[metadata]
    )
    
    msg = f"Đã ghi nhận sự kiện '{event_name}' bắt đầu lúc {start_time}. Kết thúc lúc: {end_time}."
    if location:
        msg += f" Địa điểm: {location}."
    
    if reminder_minutes > 0:
        msg += f" Thông báo nhắc trước {reminder_minutes} phút."
        
    return msg

@tool
def find_available_time_slots(date: str, schedule_context: str, start_time: str = "08:00", end_time: str = "18:00"):
    """Phân tích các khoảng trống thời gian làm việc trong một ngày (date) dựa trên lịch trình (schedule_context) từ start_time đến end_time (định dạng HH:MM)."""
    
    def parse_time(time_str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
        
    try:
        work_start = parse_time(start_time)
        work_end = parse_time(end_time)
    except ValueError:
        return "Lỗi định dạng giờ! Vui lòng sử dụng định dạng HH:MM (vd: 07:30)."

    # Extract event pairs: "Bắt đầu lúc: YYYY-MM-DD HH:MM ... Kết thúc lúc: YYYY-MM-DD HH:MM"
    event_pattern = r'Bắt đầu lúc:\s+\d{4}-\d{2}-\d{2}\s+(\d{1,2}):(\d{2}).*?Kết thúc lúc:\s+\d{4}-\d{2}-\d{2}\s+(\d{1,2}):(\d{2})'
    event_matches = re.findall(event_pattern, schedule_context, re.DOTALL)
    
    if not event_matches:
        return f"Không có lịch trình nào chiếm chỗ, bạn trống cả ngày {date} từ {start_time} đến {end_time}."
    
    busy_slots = []
    for start_h, start_m, end_h, end_m in event_matches:
        start_mins = int(start_h) * 60 + int(start_m)
        end_mins = int(end_h) * 60 + int(end_m)
        busy_slots.append((start_mins, end_mins))
    
    busy_slots.sort(key=lambda x: x[0])
    
    merged_busy = []
    for slot in busy_slots:
        if not merged_busy:
            merged_busy.append(slot)
        else:
            last = merged_busy[-1]
            if slot[0] <= last[1]:
                merged_busy[-1] = (last[0], max(last[1], slot[1]))
            else:
                merged_busy.append(slot)
                
    free_slots = []
    current_time = work_start
    
    for start, end in merged_busy:
        if current_time < start:
            free_slots.append((current_time, start))
        current_time = max(current_time, end)
        
    if current_time < work_end:
        free_slots.append((current_time, work_end))
        
    def format_time(mins):
        h = mins // 60
        m = mins % 60
        return f"{h:02d}:{m:02d}"
        
    if not free_slots:
        return f"Lịch ngày {date} của bạn đã kín mít từ {start_time} đến {end_time}, không còn khung giờ trống."
        
    result = f"Các khung giờ trống của bạn trong ngày {date} từ {start_time} đến {end_time} là:\n"
    for s, e in free_slots:
        result += f"- Từ {format_time(s)} đến {format_time(e)}\n"
        
    return result

# Khởi tạo một LLM parser dùng chính Qwen bạn đang có để tiết kiệm
parse_endpoint = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-72B-Instruct",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    temperature=0.1
)
parsing_llm = ChatHuggingFace(llm=parse_endpoint)

@tool
def check_duplicate_event(start_time: str, event_name: str) -> bool:
    """Kiểm tra xem sự kiện đã tồn tại trong Vector DB chưa."""
    date_str = start_time[:10]
    results = vector_db.get(where={"date": date_str})
    
    if not results or not results.get('metadatas'):
        return False
        
    for meta in results['metadatas']:
        # Trùng thời gian bắt đầu
        if meta.get("start_time") == start_time:
            return True
        # Trùng tên sự kiện trong cùng 1 ngày
        if meta.get("event_name", "").strip().lower() == event_name.strip().lower():
            return True
            
    return False


def extract_text_via_ocr(image_bytes: bytes) -> str:
    """Sử dụng Tesseract OCR để đọc chữ từ ảnh"""
    image = Image.open(io.BytesIO(image_bytes))
    
    # Thêm config '--psm 6' hoặc '--psm 4' để ép Tesseract cố gắng đọc cấu trúc dạng khối/cột
    raw_text = pytesseract.image_to_string(image, lang='vie+eng', config='--psm 6')
    
    # === THÊM ĐOẠN NÀY ĐỂ DEBUG TRÊN TERMINAL ===
    print("\n" + "="*20 + " KẾT QUẢ QUÉT OCR " + "="*20)
    print(raw_text)
    print("="*59 + "\n")
    # ============================================
    
    return raw_text

def validate_event_time(start_time: str, current_time: str) -> tuple[bool, str]:
    """Kiểm tra xem thời gian sự kiện có phải là quá khứ không.
    Returns: (is_valid, error_message)
    - is_valid: True nếu thời gian hợp lệ, False nếu là quá khứ
    - error_message: Thông báo lịch sự cho người dùng
    """
    try:
        event_dt = datetime.strptime(start_time[:16], "%Y-%m-%d %H:%M")
        current_dt = datetime.strptime(current_time[:16], "%Y-%m-%d %H:%M")
        
        if event_dt < current_dt:
            formatted_event = event_dt.strftime("%d/%m/%Y lúc %H:%M")
            formatted_now = current_dt.strftime("%d/%m/%Y lúc %H:%M")
            error_msg = f"⏰ **Lưu ý:** Thời gian sự kiện ({formatted_event}) đã trôi qua so với thời gian hiện tại ({formatted_now}).\n\nVui lòng kiểm tra lại thời gian hoặc ngày tháng năm cho sự kiện nhé."
            return False, error_msg
        
        return True, ""
    except ValueError:
        return False, "❌ Lỗi: Định dạng thời gian không hợp lệ."

def parse_event_with_qwen(raw_text: str, current_time: str) -> list:
    """Đưa văn bản thô từ OCR cho Qwen xử lý thành DANH SÁCH JSON"""
    prompt = f"""
    Bạn là một hệ thống chuyển đổi văn bản OCR thành mảng JSON. BẠN KHÔNG CÓ KHẢ NĂNG GIAO TIẾP.
    Thời gian hiện tại là {current_time}.
    Dưới đây là văn bản OCR từ một thời khóa biểu chứa RẤT NHIỀU môn học:
    ---
    {raw_text}
    ---
    NHIỆM VỤ BẮT BUỘC:
    1. Tìm và trích xuất TẤT CẢ các môn học/sự kiện có trong văn bản.
    2. TUYỆT ĐỐI KHÔNG ĐƯỢC LƯỜI BIẾNG BỎ SÓT. Nếu trong văn bản có 5 môn, bạn PHẢI trả về 5 object. Có 10 môn PHẢI trả về 10 object.
    3. Trả về ĐÚNG 1 MẢNG JSON (LIST) CHỨA CÁC OBJECT ĐÓ.

    CẤU TRÚC BẮT BUỘC CỦA MỖI OBJECT TRONG MẢNG:
    [
        {{
            "event_name": "Tên môn học",
            "start_time": "YYYY-MM-DD HH:MM",
            "end_time": "YYYY-MM-DD HH:MM",
            "location": "Phòng học"
        }},
        ... (Tiếp tục cho đến khi HẾT CÁC MÔN) ...
    ]
    
    QUY TẮC:
    - Tính toán ngày tháng năm YYYY-MM-DD dựa vào "{current_time}".
    - Nếu thiếu giờ bắt đầu, mặc định "07:00".
    - Nếu thiếu giờ kết thúc, cộng thêm 3 tiếng từ giờ bắt đầu.
    """
    
    response = parsing_llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()
    
    content = content.replace("```json", "").replace("```", "").strip()
    
    start_idx = content.find('[')
    end_idx = content.rfind(']')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = content[start_idx:end_idx+1]
        try:
            parsed_json = json.loads(json_str)
            if isinstance(parsed_json, dict): 
                return [parsed_json]
            return parsed_json
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"LLM trả về định dạng sai. Nội dung: {content}", content, 0)
    else:
        start_idx_dict = content.find('{')
        if start_idx_dict != -1:
            json_str = content[start_idx_dict:]
            try:
                decoder = json.JSONDecoder()
                parsed_json, _ = decoder.raw_decode(json_str)
                return [parsed_json]
            except:
                pass
        raise ValueError(f"Không tìm thấy mảng JSON nào. LLM nói: {content}")

@tool
def process_image_and_add_to_calendar(image_bytes: bytes, current_time: str) -> str:
    """Quy trình tổng hợp: Đọc OCR -> Gửi Qwen -> Xử lý mảng sự kiện -> Lưu DB hàng loạt"""
    try:
        # Bước 1: Quét chữ bằng Tesseract
        raw_text = extract_text_via_ocr(image_bytes)
        
        if len(raw_text.strip()) < 5:
            return "❌ Hình ảnh quá mờ hoặc không chứa văn bản nào có thể đọc được."

        # Bước 2: Phân tích thành MẢNG JSON
        events_list = parse_event_with_qwen(raw_text, current_time)
        
        if not events_list:
            return "❌ Không tìm thấy sự kiện/môn học nào trong hình ảnh."
        
        success_msgs = []
        error_msgs = []
        
        # Bước 3: Duyệt qua từng môn học để kiểm tra và lưu
        for event_data in events_list:
            event_name = event_data.get("event_name")
            start_time = event_data.get("start_time")
            end_time = event_data.get("end_time")
            location = event_data.get("location", "")
            
            if not event_name or not start_time or not end_time:
                error_msgs.append(f"⚠️ Thiếu thông tin cho sự kiện: {event_name or 'Không rõ tên'}")
                continue
            
            # Kiểm tra thời gian quá khứ
            is_valid_time, time_error = validate_event_time(start_time, current_time)
            if not is_valid_time:
                # Làm sạch câu lỗi cho gọn
                clean_error = time_error.replace('❌ Lỗi: ', '').replace('⏰ **Lưu ý:** ', '')
                error_msgs.append(f"⚠️ {event_name}: {clean_error}")
                continue
                
            # Kiểm tra trùng lặp (Nhớ dùng .invoke() vì đây là tool)
            is_duplicate = check_duplicate_event.invoke({
                "start_time": start_time, 
                "event_name": event_name
            })
            
            if is_duplicate:
                error_msgs.append(f"⚠️ **{event_name}** lúc {start_time[-5:]} đã có trong lịch. Bỏ qua.")
                continue
                
            # Lưu vào DB (Nhớ dùng .invoke())
            add_event_to_calendar.invoke({
                "event_name": event_name,
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "reminder_minutes": 0,
                "current_time": current_time
            })
            # Ghi nhận thành công
            success_msgs.append(f"- *{event_name}* ({start_time})")
        
        # Bước 4: Tổng hợp kết quả trả về cho giao diện
        final_output = []
        if success_msgs:
            final_output.append(f"✅ **Đã lưu thành công {len(success_msgs)} sự kiện:**\n" + "\n".join(success_msgs))
        if error_msgs:
            final_output.append(f"❌ **Các sự kiện bị bỏ qua:**\n" + "\n".join(error_msgs))
            
        if not final_output:
            return "❌ Không có sự kiện nào được xử lý."
            
        return "\n\n".join(final_output)
        
    except json.JSONDecodeError as e:
        return f"❌ Lỗi: Mô hình không thể định dạng JSON.\n\nChi tiết: {str(e)}"
    except Exception as e:
        return f"❌ Có lỗi xảy ra trong quá trình xử lý ảnh OCR: {str(e)}"