import os
import re
import json
import tempfile
import hashlib
from datetime import datetime, timedelta

import icalendar
from dotenv import load_dotenv

from llm_config import shared_llm

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_unstructured import UnstructuredLoader

# =========================================================
# ENV + PATH
# =========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
os.makedirs(BACKEND_DIR, exist_ok=True)
load_dotenv()

UNSTRUCTURED_API_KEY = os.getenv('UNSTRUCTURED_API_KEY')

# =========================================================
# EMBEDDING (ONLINE)
# =========================================================
embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
)

vector_db = Chroma(
    collection_name="schedule_events",
    embedding_function=embeddings,
    persist_directory=BACKEND_DIR,
)

# =========================================================
# KHO CHỨA TẠM BẢN DỊCH & BẢN GỐC
# =========================================================
_RAW_TEXT_CACHE = {}
_PARSED_JSON_CACHE = {} # <-- Kho chứa tạm kết quả JSON để Agent không phải ôm

def _get_file_hash(file_bytes: bytes) -> str:
    return hashlib.md5(file_bytes).hexdigest()

def filter_relevant_lines(text: str) -> str:
    lines = text.splitlines()
    keep = []
    for line in lines:
        if any(ch.isdigit() for ch in line) or "Thứ" in line:
            keep.append(line.strip())
    return "\n".join(keep[:300])

# =========================================================
# BASIC TOOLS
# =========================================================
@tool
def get_schedule_by_date(date: str):
    """Lấy danh sách các sự kiện trong một ngày cụ thể (YYYY-MM-DD)."""
    results = vector_db.get(where={"date": date})
    if not results["documents"]:
        return f"Bạn không có lịch trình nào vào ngày {date}."
    events_str = "\n".join(f"- {doc}" for doc in results["documents"])
    return f"Lịch trình ngày {date}:\n{events_str}"

@tool
def search_events(query: str, k: int = 3):
    """Tìm kiếm các sự kiện đã lưu bằng truy vấn ngữ nghĩa."""
    results = vector_db.similarity_search(query, k=k)
    if not results:
        return f"Không tìm thấy sự kiện nào liên quan tới '{query}'."
    events_str = "\n".join(f"- {doc.page_content}" for doc in results)
    return f"Các sự kiện liên quan:\n{events_str}"

@tool
def get_events_by_date_range(start_date: str, end_date: str):
    """Lấy danh sách sự kiện trong một khoảng ngày."""
    results = vector_db.get(where={"$and": [{"date": {"$gte": start_date}}, {"date": {"$lte": end_date}}]})
    if not results["documents"]:
        return f"Không có sự kiện nào từ {start_date} đến {end_date}."
    events_str = "\n".join(f"- {doc}" for doc in results["documents"])
    return f"Các sự kiện từ {start_date} đến {end_date}:\n{events_str}"

@tool
def find_available_time_slots(date: str, schedule_context: str, start_time: str = "08:00", end_time: str = "18:00"):
    """Phân tích các khung giờ trống trong một ngày dựa trên lịch đã có."""
    def parse_time(t):
        h, m = map(int, t.split(":"))
        return h * 60 + m

    try:
        work_start = parse_time(start_time)
        work_end = parse_time(end_time)
    except ValueError:
        return "❌ Lỗi định dạng giờ. Vui lòng dùng HH:MM."

    pattern = r"Bắt đầu:\s+\d{4}-\d{2}-\d{2}\s+(\d{2}):(\d{2}).*?Kết thúc:\s+\d{4}-\d{2}-\d{2}\s+(\d{2}):(\d{2})"
    matches = re.findall(pattern, schedule_context, re.DOTALL)
    if not matches:
        return f"Bạn trống cả ngày {date} từ {start_time} đến {end_time}."

    busy = [(int(sh) * 60 + int(sm), int(eh) * 60 + int(em)) for sh, sm, eh, em in matches]
    busy.sort()
    
    merged = []
    for s, e in busy:
        if not merged or s > merged[-1][1]:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)

    free = []
    cur = work_start
    for s, e in merged:
        if cur < s: free.append((cur, s))
        cur = max(cur, e)
    if cur < work_end: free.append((cur, work_end))

    def fmt(m): return f"{m//60:02d}:{m%60:02d}"

    if not free: return f"Lịch ngày {date} đã kín."
    msg = f"Các khung giờ trống ngày {date}:\n"
    for s, e in free: msg += f"- {fmt(s)} → {fmt(e)}\n"
    return msg

def validate_event_logic(start_time, end_time, event_name, current_time):
    try:
        st = datetime.strptime(start_time[:16], "%Y-%m-%d %H:%M")
        et = datetime.strptime(end_time[:16], "%Y-%m-%d %H:%M")
        ct = datetime.strptime(current_time[:16], "%Y-%m-%d %H:%M")
        if et <= st: return "❌ Thời gian kết thúc phải sau thời gian bắt đầu."
        if st < ct: return "⚠️ Sự kiện này nằm trong quá khứ."
    except Exception:
        return "❌ Định dạng thời gian không hợp lệ."
    return "VALID"

@tool
def add_event_to_calendar(event_name: str, start_time: str, end_time: str, location: str = "", reminder_minutes: int = 0, current_time: str = ""):
    """Thêm một sự kiện vào lịch sau khi kiểm tra hợp lệ."""
    if not current_time: current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    check = validate_event_logic(start_time, end_time, event_name, current_time)
    if check != "VALID": return check

    date_str = start_time[:10]
    try:
        st_obj = datetime.strptime(start_time[:16], "%Y-%m-%d %H:%M")
        rem_obj = st_obj - timedelta(minutes=int(reminder_minutes))
        rem_ts = int(rem_obj.timestamp())
    except Exception:
        rem_ts = 0

    meta = {
        "date": date_str, "event_name": event_name, "start_time": start_time,
        "end_time": end_time, "location": location, "reminder_minutes": int(reminder_minutes),
        "reminder_timestamp": rem_ts, 
    }

    text = f"{event_name}. Bắt đầu: {start_time}. Kết thúc: {end_time}."
    vector_db.add_texts([text], metadatas=[meta])
    return f"✅ Đã lưu sự kiện '{event_name}'."

def is_ics_file(file_bytes: bytes) -> bool:
    try: return "BEGIN:VCALENDAR" in file_bytes[:200].decode("utf-8", "ignore").upper()
    except Exception: return False

def extract_text_with_unstructured(file_bytes: bytes, file_name: str) -> str:
    if not UNSTRUCTURED_API_KEY:
        return "❌ Thiếu UNSTRUCTURED_API_KEY."

    file_hash = _get_file_hash(file_bytes)
    if file_hash in _RAW_TEXT_CACHE: return _RAW_TEXT_CACHE[file_hash]

    _, ext = os.path.splitext(file_name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
        f.write(file_bytes)
        path = f.name

    try:
        loader = UnstructuredLoader(file_path=path, api_key=UNSTRUCTURED_API_KEY, partition_via_api=True, chunking_strategy="by_title", strategy="hi_res", pdf_infer_table_structure=True)
        docs = loader.load()
        extracted_parts = [d.metadata["text_as_html"] if "text_as_html" in d.metadata else d.page_content for d in docs]
        text = "\n\n".join(extracted_parts)
        _RAW_TEXT_CACHE[file_hash] = text
        return text
    finally:
        try: os.remove(path)
        except Exception: pass

def parse_event_with_nvidia(raw_text: str, current_time: str, user_prompt: str = ""):
    prompt = f"""
    Bạn là một AI siêu việt trong việc bóc tách dữ liệu lịch trình từ văn bản.
    Nhiệm vụ: Trả về MỘT MẢNG JSON 2 CHIỀU chứa toàn bộ sự kiện. KHÔNG giải thích thêm.
    Cấu trúc: ["YYYY-MM-DD", "Tên sự kiện", "HH:MM (bắt đầu)", "HH:MM (kết thúc)"]
    Thời gian hiện tại: {current_time}
    Yêu cầu bổ sung: {user_prompt}
    
    VĂN BẢN THÔ CẦN XỬ LÝ:
    ---
    {raw_text}
    ---
    """
    raw_result = shared_llm.invoke([HumanMessage(content=prompt)]).content.strip()
    try:
        m = re.search(r"\[.*\]", raw_result, flags=re.DOTALL)
        if m: return json.dumps(json.loads(m.group(0)), ensure_ascii=False)
        return "[]" 
    except Exception as e:
        return f"❌ Lỗi xử lý JSON: {str(e)}"

# =========================================================
# CHỈ DÙNG MÃ FILE (FILE_HASH) ĐỂ TRUY XUẤT VÀ LƯU (CÓ TỐI ƯU HÀNG LOẠT)
# =========================================================
# =========================================================
# CHỈ DÙNG MÃ FILE (FILE_HASH) ĐỂ TRUY XUẤT VÀ LƯU (CÓ TỐI ƯU HÀNG LOẠT & LOG CONSOLE)
# =========================================================
@tool
def save_events_from_schedule_text(file_hash: str, current_time: str = ""):
    """Lưu tự động các sự kiện vào CSDL dựa trên mã file_hash. Lỗi sẽ được log ra console."""
    if not current_time: current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    schedule_text = _PARSED_JSON_CACHE.get(file_hash)
    
    if not schedule_text:
        print(f"\n[CONSOLE LOG - ERROR] file_hash '{file_hash}' không tồn tại hoặc đã hết hạn.")
        return "❌ Dữ liệu phiên làm việc đã hết hạn. Hãy yêu cầu đọc lại file."

    try:
        events = json.loads(schedule_text)
    except Exception as e:
        print(f"\n[CONSOLE LOG - ERROR] Lỗi parse JSON dữ liệu trong kho: {str(e)}")
        return "❌ Đã xảy ra sự cố kỹ thuật khi đọc dữ liệu. Vui lòng thử lại."

    if not events or not isinstance(events, list):
        return "⚠️ Tui không thấy lịch trình nào hợp lệ để lưu."

    saved = []
    errors = []
    batch_texts = []
    batch_metas = []

    for idx, ev in enumerate(events, 1):
        if not isinstance(ev, list) or len(ev) < 4: continue
        
        date_val = str(ev[0]).strip()
        name = str(ev[1]).strip()
        st_time = str(ev[2]).strip()
        et_time = str(ev[3]).strip()
        st = f"{date_val} {st_time}"
        et = f"{date_val} {et_time}"
        loc = str(ev[4]).strip() if len(ev) > 4 and ev[4] else ""
        
        try:
            rem = int(ev[5]) if len(ev) > 5 and ev[5] else 0
        except:
            rem = 0

        # Kiểm tra tính hợp lệ
        check = validate_event_logic(st, et, name, current_time)
        if check != "VALID":
            errors.append((name, check))  # Gom lỗi lại để in ra console sau
            continue

        try:
            st_obj = datetime.strptime(st[:16], "%Y-%m-%d %H:%M")
            rem_obj = st_obj - timedelta(minutes=int(rem))
            rem_ts = int(rem_obj.timestamp())
        except Exception:
            rem_ts = 0

        meta = {
            "date": date_val, "event_name": name, "start_time": st,
            "end_time": et, "location": loc, "reminder_minutes": int(rem),
            "reminder_timestamp": rem_ts, 
        }
        text = f"{name}. Bắt đầu: {st}. Kết thúc: {et}."
        
        batch_texts.append(text)
        batch_metas.append(meta)
        saved.append(name)

    # LƯU HÀNG LOẠT
    if batch_texts:
        try:
            vector_db.add_texts(batch_texts, metadatas=batch_metas)
        except Exception as e:
            print(f"\n[CONSOLE LOG - DB ERROR] Lỗi ghi CSDL hàng loạt: {str(e)}")
            return "❌ Hệ thống cơ sở dữ liệu đang gặp sự cố. Không thể lưu."

    # --- IN LỖI RA CONSOLE (TERMINAL) THAY VÌ HIỂN THỊ LÊN WEB ---
    if errors:
        print("\n" + "="*50)
        print(f"⚠️ [SYSTEM LOG] BỎ QUA {len(errors)} SỰ KIỆN DO LỖI DỮ LIỆU:")
        for err_name, err_msg in errors:
            print(f"  - Sự kiện: '{err_name}' | Nguyên nhân: {err_msg}")
        print("="*50 + "\n")

    # TRẢ KẾT QUẢ GỌN GÀNG CHO WEB
    if not saved:
        return "⚠️ Không có sự kiện nào được lưu thành công."
        
    return f"✅ Tui đã lưu thành công {len(saved)} sự kiện vào hệ thống!"

@tool
def process_schedule_file(file_path: str, current_time: str, user_prompt: str = ""):
    """Xử lý file lịch đính kèm. Khai thác dữ liệu, lưu vào kho tạm và trả về mã file_hash."""
    if not os.path.exists(file_path): return f"❌ Không tìm thấy file tại: {file_path}"
        
    with open(file_path, "rb") as f: file_bytes = f.read()
    file_name = os.path.basename(file_path)
    
    raw_text = extract_text_with_unstructured(file_bytes, file_name)
    if not raw_text or len(raw_text.strip()) < 20: return "❌ Tui không đọc được nội dung có ý nghĩa từ file này."

    parsed_text = parse_event_with_nvidia(raw_text, current_time, user_prompt)
    
    # KHI PHÂN TÍCH XONG, LƯU VÀO KHO TẠM
    file_hash = _get_file_hash(file_bytes)
    _PARSED_JSON_CACHE[file_hash] = parsed_text
    
    try:
        count = len(json.loads(parsed_text))
    except:
        count = 0
    
    # CHỈ TRẢ VỀ CHO AGENT MỘT THÔNG BÁO VÀ MÃ HASH NGẮN GỌN
    return f"Đã trích xuất thành công {count} sự kiện. [file_hash: {file_hash}]"