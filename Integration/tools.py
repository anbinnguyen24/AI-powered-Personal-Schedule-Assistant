import os
import re
import json
import tempfile
import hashlib
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from llm_config import shared_llm
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_unstructured import UnstructuredLoader

# === THÊM Ở ĐẦU FILE ===
_vector_db = None
_embeddings = None

def get_vector_db():
    global _vector_db, _embeddings
    if _vector_db is None:
        _embeddings = HuggingFaceEndpointEmbeddings(
            model="sentence-transformers/all-MiniLM-L6-v2",
            huggingfacehub_api_token=os.getenv("HF_TOKEN"),
        )
        _vector_db = Chroma(
            collection_name="schedule_events",
            embedding_function=_embeddings,
            persist_directory=BACKEND_DIR,
        )
    return _vector_db

# =========================================================
# ENV + PATH
# =========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
os.makedirs(BACKEND_DIR, exist_ok=True)
load_dotenv()
UNSTRUCTURED_API_KEY = os.getenv('UNSTRUCTURED_API_KEY')

# =========================================================
# KHO CHỨA TẠM BẢN DỊCH & BẢN GỐC
# =========================================================
_RAW_TEXT_CACHE = {}
_PARSED_JSON_CACHE = {}  # <-- Kho chứa tạm kết quả JSON để Agent không phải ôm

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
    results = get_vector_db().get(where={"date": date})
    if not results["documents"]:
        return f"Bạn không có lịch trình nào vào ngày {date}."
    events_str = "\n".join(f"- {doc}" for doc in results["documents"])
    return f"Lịch trình ngày {date}:\n{events_str}"

@tool
def search_events(query: str, k: int = 3):
    """Tìm kiếm các sự kiện đã lưu bằng truy vấn ngữ nghĩa."""
    results = get_vector_db().similarity_search(query, k=k)
    if not results:
        return f"Không tìm thấy sự kiện nào liên quan tới '{query}'."
    events_str = "\n".join(f"- {doc.page_content}" for doc in results)
    return f"Các sự kiện liên quan:\n{events_str}"

@tool
def get_events_by_date_range(start_date: str, end_date: str):
    """Lấy danh sách sự kiện trong một khoảng ngày."""
    results = get_vector_db().get(
        where={"$and": [{"date": {"$gte": start_date}}, {"date": {"$lte": end_date}}]}
    )
    if not results["documents"]:
        return f"Không có sự kiện nào từ {start_date} đến {end_date}."
    events_str = "\n".join(f"- {doc}" for doc in results["documents"])
    return f"Các sự kiện từ {start_date} đến {end_date}:\n{events_str}"

@tool
def find_available_time_slots(
    date: str,
    start_time: str = "00:00",
    end_time: str = "23:59", # Đổi mặc định đến hết ngày cho thực tế
    current_time: str = ""
):
    """Phân tích các khung giờ trống trong một ngày cụ thể (AI KHÔNG CẦN truyền schedule_context, hàm sẽ tự lấy)."""
    def parse_time(t):
        h, m = map(int, t.split(":"))
        return h * 60 + m

    try:
        work_start = parse_time(start_time)
        work_end = parse_time(end_time)

        # Chặn tìm giờ rảnh trong quá khứ
        if current_time:
            try:
                now_dt = datetime.strptime(current_time[:16], "%Y-%m-%d %H:%M")
                if date == now_dt.strftime("%Y-%m-%d"):
                    now_in_minutes = now_dt.hour * 60 + now_dt.minute
                    work_start = max(work_start, now_in_minutes)
            except Exception:
                pass
        
        if work_start >= work_end:
            return f"Đã hết thời gian trong ngày {date} để tìm khung giờ trống."

    except ValueError:
        return "❌ Lỗi định dạng giờ. Vui lòng dùng HH:MM."

    # ✨ ĐÂY LÀ CHÌA KHÓA: Hàm TỰ ĐỘNG vào Database lấy lịch, cắt đuôi LLM trung gian
    results = get_vector_db().get(where={"date": date})
    documents = results.get("documents", [])
    schedule_context = "\n".join(documents) if documents else ""

    # Cập nhật Regex bắt luôn cả ngày tháng để xử lý lịch qua đêm
    pattern = r"Bắt đầu:\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2}).*?Kết thúc:\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2})"
    matches = re.findall(pattern, schedule_context, re.DOTALL)

    if not matches:
        def fmt_time(m): return f"{m//60:02d}:{m%60:02d}"
        return f"Bạn trống cả ngày {date} từ {fmt_time(work_start)} đến {end_time}."

    busy = []
    for st_date, sh, sm, et_date, eh, em in matches:
        s_min = int(sh) * 60 + int(sm)
        e_min = int(eh) * 60 + int(em)
        
        # Sửa lỗi tính toán lịch qua đêm (Ví dụ: Ngủ từ 23:20 -> 05:45)
        if et_date > st_date or e_min <= s_min:
            e_min += 24 * 60
        busy.append((s_min, e_min))
    
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
        if cur < s:
            if s > work_end:
                free.append((cur, work_end))
                cur = work_end
                break
            free.append((cur, s))
        cur = max(cur, e)

    if cur < work_end:
        free.append((cur, work_end))

    def fmt(m):
        m = m % (24 * 60) # Chống tràn 24h
        return f"{m//60:02d}:{m%60:02d}"

    if not free:
        return f"Lịch ngày {date} từ {start_time} đến {end_time} đã kín."

    msg = f"Các khung giờ trống ngày {date}:\n"
    for s, e in free:
        msg += f"- {fmt(s)} → {fmt(e)}\n"
    return msg

def validate_event_logic(start_time, end_time, event_name, current_time, exclude_event_name=None):
    try:
        st = datetime.strptime(start_time[:16], "%Y-%m-%d %H:%M")
        et = datetime.strptime(end_time[:16], "%Y-%m-%d %H:%M")
        ct = datetime.strptime(current_time[:16], "%Y-%m-%d %H:%M")
        if et <= st:
            return "❌ Thời gian kết thúc phải sau thời gian bắt đầu."
        if st < ct:
            return "⚠️ Sự kiện này nằm trong quá khứ."
    except Exception:
        return "❌ Định dạng thời gian không hợp lệ."

    # KIỂM TRA TRÙNG LỊCH TRONG DATABASE
    try:
        db = get_vector_db()
        # Lấy ngày của sự kiện và ngày hôm trước (để cover các sự kiện kéo dài xuyên đêm)
        curr_date = st.strftime("%Y-%m-%d")
        prev_date = (st - timedelta(days=1)).strftime("%Y-%m-%d")
        
        results = db.get(where={"$or": [{"date": curr_date}, {"date": prev_date}]})
        
        if results and results.get("metadatas"):
            for meta in results["metadatas"]:
                if not meta:
                    continue
                    
                existing_name = meta.get("event_name", "").strip()
                
                # Bỏ qua sự kiện cũ đang được sửa (để không tự báo trùng với chính mình)
                if exclude_event_name and existing_name.lower() == exclude_event_name.strip().lower():
                    continue
                    
                ext_st_str = meta.get("start_time", "")
                ext_et_str = meta.get("end_time", "")
                
                if ext_st_str and ext_et_str:
                    ext_st = datetime.strptime(ext_st_str[:16], "%Y-%m-%d %H:%M")
                    ext_et = datetime.strptime(ext_et_str[:16], "%Y-%m-%d %H:%M")
                    
                    # Logic phát hiện trùng lặp thời gian: (Bắt đầu A < Kết thúc B) VÀ (Kết thúc A > Bắt đầu B)
                    if st < ext_et and et > ext_st:
                        time_overlap = f"{ext_st.strftime('%H:%M')} -> {ext_et.strftime('%H:%M')}"
                        return f"❌ Trùng lịch! Bạn đã có sự kiện '{existing_name}' vào khung giờ {time_overlap}."
    except Exception:
        pass # Nếu có lỗi lấy DB thì tạm bỏ qua (tránh sập app)

    return "VALID"

@tool
def add_event_to_calendar(
    event_name: str,
    start_time: str,
    end_time: str,
    location: str = "",
    reminder_minutes: int = 0,
    current_time: str = "",
):
    """Thêm một sự kiện vào lịch sau khi kiểm tra hợp lệ."""
    if not current_time:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    check = validate_event_logic(start_time, end_time, event_name, current_time)
    if check != "VALID":
        return check

    date_str = start_time[:10]
    try:
        st_obj = datetime.strptime(start_time[:16], "%Y-%m-%d %H:%M")
        rem_obj = st_obj - timedelta(minutes=int(reminder_minutes))
        rem_ts = int(rem_obj.timestamp())
    except Exception:
        rem_ts = 0

    capitalized_name = event_name.capitalize()
    capitalized_location = location.title() if location else ""

    meta = {
        "date": date_str,
        "event_name": capitalized_name,
        "start_time": start_time,
        "end_time": end_time,
        "location": capitalized_location,
        "reminder_minutes": int(reminder_minutes),
        "reminder_timestamp": rem_ts,
    }

    text = f"{capitalized_name}. Bắt đầu: {start_time}. Kết thúc: {end_time}."
    get_vector_db().add_texts([text], metadatas=[meta])
    return f"✅ Đã lưu sự kiện '{capitalized_name}'."

def is_ics_file(file_bytes: bytes) -> bool:
    try:
        return "BEGIN:VCALENDAR" in file_bytes[:200].decode("utf-8", "ignore").upper()
    except Exception:
        return False

def extract_text_with_unstructured(file_bytes: bytes, file_name: str) -> str:
    if not UNSTRUCTURED_API_KEY:
        return "❌ Thiếu UNSTRUCTURED_API_KEY."

    file_hash = _get_file_hash(file_bytes)
    if file_hash in _RAW_TEXT_CACHE:
        return _RAW_TEXT_CACHE[file_hash]

    _, ext = os.path.splitext(file_name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
        f.write(file_bytes)
        path = f.name

    try:
        loader = UnstructuredLoader(
            file_path=path,
            api_key=UNSTRUCTURED_API_KEY,
            partition_via_api=True,
            chunking_strategy="by_title",
            strategy="fast",
        )
        docs = loader.load()
        extracted_parts = [
            d.metadata["text_as_html"] if "text_as_html" in d.metadata else d.page_content
            for d in docs
        ]
        text = "\n\n".join(extracted_parts)
        _RAW_TEXT_CACHE[file_hash] = text
        return text
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

def parse_event_with_nvidia(raw_text: str, current_time: str, user_prompt: str = ""):
    # 1. THAY ĐỔI PROMPT: Nén định dạng thành 1 dòng duy nhất dùng dấu "|"
    prompt = f"""
    Bạn là một AI siêu việt trong việc bóc tách dữ liệu lịch trình từ văn bản.
    Nhiệm vụ: Trích xuất toàn bộ sự kiện và trả về dưới dạng VĂN BẢN THUẦN (TXT). TUYỆT ĐỐI KHÔNG DÙNG JSON.

    Cú pháp BẮT BUỘC (Mỗi sự kiện nằm trên đúng 1 dòng, phân cách bởi dấu | tạo thành 5 cột):
    YYYY-MM-DD|Tên sự kiện|HH:MM|HH:MM|Địa điểm

    Ví dụ chuẩn:
    2026-03-29|Tập thể dục|06:00|06:30|Phòng Gym Cali
    2026-03-30|Đi ngủ|23:20|05:45|

    Thời gian hiện tại: {current_time}
    Yêu cầu bổ sung: {user_prompt}

    LƯU Ý ĐẶC BIỆT:
    - AI tự hiểu ngữ nghĩa văn bản để suy luận ra ngày tháng, sự kiện và địa điểm.
    - Đảm bảo giờ luôn là định dạng 24h (ví dụ: 5h45 -> 05:45).
    - Nếu không đề cập đến địa điểm, cứ để trống phía sau dấu | cuối cùng.
    - KHÔNG CẦN CHÈN CHỮ "Ngày hôm sau", chỉ cần trích xuất đúng giờ.
    - Tuyệt đối không sinh ra bất kỳ ký tự nào khác, không chào hỏi, không giải thích.
    - BẮT BUỘC TRÍCH XUẤT ĐẦY ĐỦ TẤT CẢ CÁC NGÀY (Không được bỏ sót bất kỳ ngày nào).

    VĂN BẢN THÔ CẦN XỬ LÝ:
    ---
    {raw_text}
    ---
    """
    # 2. GỌI AI
    response = shared_llm.invoke([HumanMessage(content=prompt)])
    raw_result = response.content.strip() if isinstance(response.content, str) else str(response.content).strip()

    # 3. DÙNG PYTHON ĐỂ ĐÓNG GÓI LẠI THÀNH JSON
    # Cắt văn bản theo dòng và tách bằng dấu '|'
    try:
        lines = [ln.strip() for ln in raw_result.splitlines() if ln.strip() and '|' in ln]
        events = []
        
        for line in lines:
            parts = [p.strip() for p in line.split('|')]
            # Lấy các dòng có ít nhất 4 phần tử. Địa điểm là phần tử thứ 5 (nếu có)
            if len(parts) >= 4:
                location = parts[4] if len(parts) >= 5 else ""
                events.append([parts[0], parts[1], parts[2], parts[3], location])
                
        return json.dumps(events, ensure_ascii=False)
    except Exception as e:
        return f"❌ Lỗi xử lý dữ liệu từ AI: {str(e)}"

# =========================================================
# CHỈ DÙNG MÃ FILE (FILE_HASH) ĐỂ TRUY XUẤT VÀ LƯU (CÓ TỐI ƯU HÀNG LOẠT & LOG CONSOLE)
# =========================================================
@tool
def save_events_from_schedule_text(file_hash: str, current_time: str = ""):
    """Lưu tự động các sự kiện vào CSDL. Tự xử lý lịch xuyên đêm (Ngày hôm sau)."""
    if not current_time:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    schedule_text = _PARSED_JSON_CACHE.get(file_hash)
    if not schedule_text:
        return "❌ Dữ liệu phiên làm việc đã hết hạn. Hãy yêu cầu đọc lại file."

    try:
        events = json.loads(schedule_text)
    except Exception as e:
        return f"❌ Lỗi cấu trúc dữ liệu: {str(e)}"

    saved, errors, batch_texts, batch_metas = [], [], [], []

    for ev in events:
        if not isinstance(ev, list) or len(ev) < 4:
            continue

        date_val = str(ev[0]).strip()
        name = str(ev[1]).strip().capitalize()  # Viết hoa đầu câu cho đẹp
        st_time = str(ev[2]).strip()
        et_time = str(ev[3]).strip()

        # 💡 LOGIC XỬ LÝ "NGÀY HÔM SAU"
        try:
            st_dt = datetime.strptime(f"{date_val} {st_time}", "%Y-%m-%d %H:%M")
            et_dt = datetime.strptime(f"{date_val} {et_time}", "%Y-%m-%d %H:%M")
            # Nếu giờ kết thúc <= giờ bắt đầu (vd: 23:20 -> 05:45), tự hiểu là sang ngày hôm sau
            if et_dt <= st_dt:
                et_dt += timedelta(days=1)
            st, et = st_dt.strftime("%Y-%m-%d %H:%M"), et_dt.strftime("%Y-%m-%d %H:%M")
        except:
            st, et = f"{date_val} {st_time}", f"{date_val} {et_time}"

        loc = str(ev[4]).strip().title() if len(ev) > 4 and ev[4] else ""
        try:
            rem = int(ev[5]) if len(ev) > 5 and ev[5] else 0
        except:
            rem = 0

        check = validate_event_logic(st, et, name, current_time)
        if check != "VALID":
            errors.append((name, check, st, et))
            continue

        # Chuẩn bị Metadata để lưu
        meta = {
            "date": date_val,
            "event_name": name,
            "start_time": st,
            "end_time": et,
            "location": loc,
            "reminder_minutes": rem,
            "reminder_timestamp": int(datetime.strptime(st, "%Y-%m-%d %H:%M").timestamp() - rem * 60),
        }

        batch_texts.append(f"{name}. Bắt đầu: {st}. Kết thúc: {et}.")
        batch_metas.append(meta)
        saved.append(name)

    # ✅ (SỬA LỖI HIỆU NĂNG) Flush ra DB 1 lần (hoặc theo chunk) sau khi gom xong
    if batch_texts:
        db = get_vector_db()

        # ✅ TỐI ƯU NHANH NHẤT: Embedding reuse theo (event_name + location)
        # Mục tiêu: với lịch lặp (như file của bạn), số lần embed giảm cực mạnh
        if _embeddings is not None:
            embed_keys = []
            for meta in batch_metas:
                nm = meta.get("event_name", "")
                lc = meta.get("location", "")
                key = f"{nm} {lc}".strip()
                embed_keys.append(key if key else nm)

            # Unique keys (giữ thứ tự)
            unique_keys = list(dict.fromkeys(embed_keys))
            unique_vecs = _embeddings.embed_documents(unique_keys)
            key2vec = dict(zip(unique_keys, unique_vecs))
            aligned_vecs = [key2vec[k] for k in embed_keys]

            ids = [str(uuid.uuid4()) for _ in batch_texts]

            CHUNK = 500  # file bạn ~126 events -> 1 chunk là đủ, rất nhanh
            for i in range(0, len(batch_texts), CHUNK):
                db._collection.add(
                    ids=ids[i:i + CHUNK],
                    documents=batch_texts[i:i + CHUNK],
                    metadatas=batch_metas[i:i + CHUNK],
                    embeddings=aligned_vecs[i:i + CHUNK],
                )
        else:
            # Fallback: giữ nguyên cơ chế add_texts cũ
            db.add_texts(batch_texts, metadatas=batch_metas)

    # --- BÁO CÁO CHI TIẾT LÊN WEB ---
    result_msg = f"✅ **Đã lưu thành công {len(saved)} sự kiện.**\n" if saved else "⚠️ **Không có sự kiện nào được lưu.**\n"
    if errors:
        result_msg += f"\n❌ **Bỏ qua {len(errors)} sự kiện do lỗi**"
        print(" DANH SÁCH LỖI (CHỈ HIỆN Ở TERMINAL) ")
        for err_name, err_reason, st, et in errors:
            print(
                f" Sự kiện: '{err_name}' \n"
                f" Thời gian: {st} - {et} \n"
                f" Lý do: {err_reason}"
            )
    return result_msg.strip()

@tool
def process_schedule_file(file_path: str, current_time: str, user_prompt: str = ""):
    """Xử lý file lịch đính kèm. Khai thác dữ liệu, lưu vào kho tạm và trả về mã file_hash."""
    if not os.path.exists(file_path):
        return f"❌ Không tìm thấy file tại: {file_path}"

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    file_name = os.path.basename(file_path)

    # Cache theo file_hash để không phải xử lý lại nếu cùng file
    file_hash = _get_file_hash(file_bytes)
    if file_hash in _PARSED_JSON_CACHE:
        try:
            count = len(json.loads(_PARSED_JSON_CACHE[file_hash]))
        except:
            count = 0
        return f"Đã trích xuất thành công {count} sự kiện. [file_hash: {file_hash}]"

    raw_text = extract_text_with_unstructured(file_bytes, file_name)
    if not raw_text or len(raw_text.strip()) < 20:
        return "❌ Tui không đọc được nội dung có ý nghĩa từ file này."

    # =======================================================
    # BẮT ĐẦU SỬA: LỌC TRÙNG LẶP & TINH GỌN TIÊU ĐỀ
    # =======================================================
    # 1. Chỉ lấy 300 ký tự đầu tiên làm tiêu đề để AI không bị nhầm với nội dung
    header_context = raw_text[:300] if len(raw_text) > 300 else raw_text

    paragraphs = raw_text.split('\n\n')
    chunks = []
    curr_chunk = ""
    
    # Gom các đoạn văn bản lại sao cho mỗi khối không vượt quá 3000 ký tự
    for p in paragraphs:
        if len(curr_chunk) + len(p) < 3000:
            curr_chunk += p + "\n\n"
        else:
            chunks.append(curr_chunk.strip())
            curr_chunk = p + "\n\n"
    if curr_chunk.strip():
        chunks.append(curr_chunk.strip())

    all_events = []
    
    # Cho AI đọc và bóc tách từng đoạn nhỏ
    for i, chunk in enumerate(chunks):
        if len(chunk) > 10:  # Bỏ qua các đoạn quá ngắn hoặc rỗng
            if i > 0:
                chunk_to_process = f"[THÔNG TIN NGÀY THÁNG BẮT BUỘC DÙNG LÀM CHUẨN]:\n{header_context}\n\n[DỮ LIỆU CẦN BÓC TÁCH TIẾP THEO]:\n{chunk}"
            else:
                chunk_to_process = chunk

            parsed_chunk_json = parse_event_with_nvidia(chunk_to_process, current_time, user_prompt)
            try:
                events_list = json.loads(parsed_chunk_json)
                if isinstance(events_list, list):
                    all_events.extend(events_list)  # Gộp sự kiện vào mảng chung
            except Exception:
                pass

    # 2. BƯỚC QUAN TRỌNG: LỌC SẠCH SỰ KIỆN TRÙNG LẶP
    unique_events = []
    seen = set()
    
    for ev in all_events:
        if isinstance(ev, list) and len(ev) >= 4:
            # Tạo một "chữ ký" cho mỗi sự kiện: (Ngày|Tên|Bắt đầu|Kết thúc)
            date_val = str(ev[0]).strip()
            name_val = str(ev[1]).strip().lower() # Chuyển chữ thường để dễ so sánh
            start_val = str(ev[2]).strip()
            end_val = str(ev[3]).strip()
            
            event_signature = f"{date_val}|{name_val}|{start_val}|{end_val}"
            
            # Nếu chữ ký này chưa từng xuất hiện thì mới thêm vào danh sách
            if event_signature not in seen:
                seen.add(event_signature)
                unique_events.append(ev)

    # Đóng gói lại thành 1 chuỗi JSON duy nhất
    parsed_text = json.dumps(unique_events, ensure_ascii=False)
    # =======================================================

    # KHI PHÂN TÍCH XONG, LƯU VÀO KHO TẠM
    _PARSED_JSON_CACHE[file_hash] = parsed_text

    count = len(unique_events)
    # CHỈ TRẢ VỀ CHO AGENT MỘT THÔNG BÁO VÀ MÃ HASH NGẮN GỌN
    return f"Đã trích xuất thành công {count} sự kiện. [file_hash: {file_hash}]"

@tool
def edit_event_in_calendar(
    old_event_name: str,
    event_date: str,
    new_event_name: str = "",
    new_start_time: str = "",
    new_end_time: str = "",
    new_location: str = "",
    new_reminder_minutes: int = -1,
    current_time: str = "",
):
    """Sửa một sự kiện đã có trong lịch. Cần cung cấp tên sự kiện cũ và ngày (YYYY-MM-DD) để tìm."""
    if not current_time:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db = get_vector_db()
    results = db.get(where={"date": event_date})

    if not results or not results.get("ids"):
        return f"❌ Lỗi thao tác: Không có bất kỳ sự kiện nào trong ngày {event_date} để sửa."

    doc_id = None
    old_meta = {}
    
    # Ép kiểu an toàn chống AI truyền None
    old_event_name = old_event_name or ""
    target_name = old_event_name.strip().lower()
    available_events = []
    
    # 2. Dùng Python tìm kiếm linh hoạt và CHỐNG LỖI NoneType metadata
    for i, meta in enumerate(results["metadatas"]):
        if not meta:  # Bỏ qua nếu sự kiện cũ trong DB bị lỗi mất metadata
            continue
            
        ev_name = meta.get("event_name", "").strip()
        if ev_name:
            available_events.append(ev_name)
            
        if ev_name.lower() == target_name:
            doc_id = results["ids"][i]
            old_meta = meta
            break

    if not doc_id:
        return f"❌ Lỗi thao tác: Không tìm thấy '{old_event_name}'. Lịch ngày {event_date} chỉ có: {', '.join(available_events)}"

    # 3. CHUẨN HÓA DỮ LIỆU ĐẦU VÀO (Chống AI truyền None)
    new_event_name = new_event_name or ""
    new_start_time = new_start_time or ""
    new_end_time = new_end_time or ""
    new_location = new_location or ""

    final_name = new_event_name.strip().capitalize() if new_event_name.strip() else old_meta.get("event_name", "")
    
    def normalize_time(t_str, default_date):
        t_str = t_str.strip()
        if not t_str: return ""
        if len(t_str) <= 8 and ":" in t_str:  # Chỉ có giờ (VD: 08:30)
            return f"{default_date} {t_str[:5]}"
        return t_str

    parsed_new_start = normalize_time(new_start_time, event_date)
    parsed_new_end = normalize_time(new_end_time, event_date)

    final_start = parsed_new_start if parsed_new_start else old_meta.get("start_time", "")
    final_end = parsed_new_end if parsed_new_end else old_meta.get("end_time", "")

    # Xử lý Logic dời lịch (Tự động kéo dài giờ kết thúc)
    if parsed_new_start and not parsed_new_end:
        try:
            old_st_dt = datetime.strptime(old_meta.get("start_time", "")[:16], "%Y-%m-%d %H:%M")
            old_et_dt = datetime.strptime(old_meta.get("end_time", "")[:16], "%Y-%m-%d %H:%M")
            duration = old_et_dt - old_st_dt
            
            new_st_dt = datetime.strptime(final_start[:16], "%Y-%m-%d %H:%M")
            final_end = (new_st_dt + duration).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    final_loc = new_location.strip().title() if new_location.strip() else old_meta.get("location", "")
    rem_mins = int(new_reminder_minutes) if new_reminder_minutes != -1 else old_meta.get("reminder_minutes", 0)

    # 4. KIỂM TRA TRÙNG LẶP (Chống lưu vô nghĩa)
    if (final_name == old_meta.get("event_name", "") and
        final_start == old_meta.get("start_time", "") and
        final_end == old_meta.get("end_time", "") and
        final_loc == old_meta.get("location", "") and
        rem_mins == old_meta.get("reminder_minutes", 0)):
        return "⚠️ Thông tin cập nhật hoàn toàn trùng khớp với dữ liệu cũ. Không có thay đổi nào được thực hiện."

    # 5. GỌI HÀM CHECK VALID LOGIC
    check = validate_event_logic(final_start, final_end, final_name, current_time,exclude_event_name=old_event_name)
    if check != "VALID":
        return f"❌ Cập nhật thất bại: {check}"

    # 6. Tiến hành cập nhật vào Database
    date_str = final_start[:10]
    try:
        st_obj = datetime.strptime(final_start[:16], "%Y-%m-%d %H:%M")
        rem_obj = st_obj - timedelta(minutes=rem_mins)
        rem_ts = int(rem_obj.timestamp())
    except Exception:
        rem_ts = 0

    new_meta = {
        "date": date_str,
        "event_name": final_name,
        "start_time": final_start,
        "end_time": final_end,
        "location": final_loc,
        "reminder_minutes": rem_mins,
        "reminder_timestamp": rem_ts,
    }

    new_text = f"{final_name}. Bắt đầu: {final_start}. Kết thúc: {final_end}."

    try:
        db._collection.delete(ids=[doc_id])
        db.add_texts([new_text], metadatas=[new_meta])
        return f"✅ Đã cập nhật sự kiện thành: '{final_name}' ({final_start} -> {final_end})."
    except Exception as e:
        return f"❌ Có lỗi xảy ra khi cập nhật Database: {str(e)}"

@tool
def delete_event_in_calendar(event_name: str, date: str):
    """Xóa một sự kiện khỏi lịch. Cần cung cấp chính xác tên sự kiện và ngày (YYYY-MM-DD)."""
    db = get_vector_db()

    # Tương tự như sửa, lấy hết sự kiện trong ngày ra tìm
    results = db.get(where={"date": date})

    if not results or not results.get("ids"):
        return f"❌ Lỗi thao tác: Không có bất kỳ sự kiện nào trong ngày {date} để xóa."

    doc_id = None
    target_name = event_name.strip().lower()
    available_events = []
    
    for i, meta in enumerate(results["metadatas"]):
        ev_name = meta.get("event_name", "").strip()
        available_events.append(ev_name)
        if ev_name.lower() == target_name:
            doc_id = results["ids"][i]
            break

    if not doc_id:
        return f"❌ Lỗi thao tác: Không tìm thấy '{event_name}'. Lịch ngày {date} chỉ có: {', '.join(available_events)}"

    try:
        db._collection.delete(ids=[doc_id])
        return f"✅ Đã xóa thành công sự kiện '{event_name.capitalize()}' vào ngày {date} khỏi lịch trình."
    except Exception as e:
        return f"❌ Có lỗi xảy ra khi xóa dữ liệu: {str(e)}"
