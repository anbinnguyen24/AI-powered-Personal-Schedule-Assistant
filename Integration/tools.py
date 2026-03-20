import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpointEmbeddings, ChatHuggingFace
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

# Khởi tạo mô hình Embedding qua Inference API (sử dụng Qwen thay vì sentence-transformers)
embeddings = HuggingFaceEndpointEmbeddings(
    model="Qwen/Qwen2-7B",
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
    # Yêu cầu Tesseract đọc cả tiếng Việt và tiếng Anh
    # Lưu ý: Nếu Windows bị lỗi không tìm thấy tesseract, bạn cần trỏ đường dẫn ở đây, ví dụ:
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    raw_text = pytesseract.image_to_string(image, lang='vie+eng')
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

def parse_event_with_qwen(raw_text: str, current_time: str) -> dict:
    """Đưa văn bản thô từ OCR cho Qwen xử lý thành JSON"""
    prompt = f"""
    Bạn là một trợ lý trích xuất lịch trình cực kỳ chính xác. Thời gian hiện tại là {current_time}.
    Dưới đây là văn bản được quét (OCR) từ một hình ảnh (có thể có chút lỗi chính tả do máy quét):
    ---
    {raw_text}
    ---
    Hãy đọc văn bản trên và đoán/trích xuất thông tin sự kiện.
    TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON SAU, KHÔNG CÓ BẤT KỲ VĂN BẢN MARKDOWN NÀO KHÁC:
    {{
        "event_name": "Tên sự kiện ngắn gọn",
        "start_time": "YYYY-MM-DD HH:MM",
        "end_time": "YYYY-MM-DD HH:MM",
        "location": "Địa điểm (nếu có, không thì để chuỗi rỗng)"
    }}
    Chú ý: Tính toán và format ngày tháng (YYYY-MM-DD) hợp lý. Nếu không có giờ kết thúc, hãy ước lượng cộng thêm 1 tiếng từ giờ bắt đầu.
    """
    
    response = parsing_llm.invoke([HumanMessage(content=prompt)])
    clean_json_str = response.content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json_str)

@tool
def process_image_and_add_to_calendar(image_bytes: bytes, current_time: str) -> str:
    """Quy trình tổng hợp: Đọc OCR -> Gửi Qwen -> Check Thời gian -> Check Trùng -> Lưu DB"""
    try:
        # Bước 1: Quét chữ bằng Tesseract
        raw_text = extract_text_via_ocr(image_bytes)
        
        if len(raw_text.strip()) < 5:
            return "❌ Hình ảnh quá mờ hoặc không chứa văn bản nào có thể đọc được."

        # Bước 2: Phân tích thành JSON
        event_data = parse_event_with_qwen(raw_text, current_time)
        
        event_name = event_data.get("event_name")
        start_time = event_data.get("start_time")
        end_time = event_data.get("end_time")
        location = event_data.get("location", "")
        
        if not event_name or not start_time or not end_time:
            return "❌ Không thể nhận diện đầy đủ thông tin thời gian từ văn bản trong ảnh."
        
        # Bước 3: Kiểm tra thời gian quá khứ
        is_valid_time, time_error = validate_event_time(start_time, current_time)
        if not is_valid_time:
            return time_error
            
        # Bước 4: Kiểm tra trùng lặp
        is_duplicate = check_duplicate_event(start_time, event_name)
        
        if is_duplicate:
            return f"⚠️ Sự kiện **{event_name}** lúc **{start_time}** đã có trong lịch. Bỏ qua lưu mới."
            
        # Bước 5: Lưu vào DB
        result_msg = add_event_to_calendar(
            event_name=event_name,
            start_time=start_time,
            end_time=end_time,
            location=location,
            reminder_minutes=0,
            current_time=current_time
        )
        return f"✅ **Đã đọc chữ từ ảnh thành công!**\n- Trích xuất được: *{event_name}*\n- {result_msg}"
        
    except json.JSONDecodeError:
        return f"❌ Lỗi: Mô hình không thể định dạng JSON. Văn bản gốc đọc được: {raw_text[:100]}..."
    except Exception as e:
        return f"❌ Có lỗi xảy ra trong quá trình xử lý ảnh OCR: {str(e)}"