
import os
import re
import json
import time
import shutil
import random
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

from langchain_unstructured import UnstructuredLoader
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings, ChatNVIDIA
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader

load_dotenv()

DB_DIR = './chroma_db'
DATA_DIR = './data'
SINGLE_FILE_NAME = 'VIET-NAM-VAN-HOA-VA-DU-LICH.pdf'
COLLECTION_NAME = 'personal_schedule'
BUILD_VERSION = '2.1'
META_FILE = os.path.join(DB_DIR, 'build_meta.json')
CLASSIFY_CACHE_FILE = os.path.join(DB_DIR, 'classification_cache.json')
VALIDATION_CACHE_FILE = os.path.join(DB_DIR, 'validation_cache.json')

TEMPORAL_KEYWORDS = [
    'hôm nay', 'ngày mai', 'ngày mốt', 'tuần này', 'tuần sau', 'tháng này',
    'tháng sau', 'sắp tới', 'kế tiếp', 'hiện tại', 'bao giờ', 'khi nào'
]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_json(path: str, default: Any) -> Any:
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path: str, data: Any) -> None:
    ensure_dir(os.path.dirname(path) or '.')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_today_key() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def get_file_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8', errors='ignore')).hexdigest()


def create_chat_llm(temperature: float = 0.0) -> ChatNVIDIA:
    return ChatNVIDIA(
        model='meta/llama-3.1-70b-instruct',
        nvidia_api_key=os.environ.get('NVIDIA_API_KEY'),
        temperature=temperature,
    )


def create_embeddings() -> NVIDIAEmbeddings:
    return NVIDIAEmbeddings(
        model='nvidia/nv-embed-v1',
        nvidia_api_key=os.environ.get('NVIDIA_API_KEY')
    )


def invoke_with_retry(llm: ChatNVIDIA, prompt: str, max_retries: int = 6, base_delay: float = 2.0):
    last_error = None
    for attempt in range(max_retries):
        try:
            return llm.invoke(prompt)
        except Exception as e:
            last_error = e
            msg = str(e).lower()
            if any(k in msg for k in ['429', 'too many requests', 'rate limit', 'quota']):
                sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f'⚠️ Gặp rate limit. Đợi {sleep_time:.1f}s rồi thử lại...')
                time.sleep(sleep_time)
                continue
            raise
    raise RuntimeError(f'Đã retry nhiều lần nhưng vẫn lỗi: {last_error}')


def needs_temporal_context(query: str) -> bool:
    q = query.lower()
    return any(keyword in q for keyword in TEMPORAL_KEYWORDS)


def get_current_date_vn() -> str:
    current_date = datetime.now().strftime('%A, ngày %d tháng %m năm %Y')
    days_vn = {
        'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
        'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
    }
    for en, vn in days_vn.items():
        current_date = current_date.replace(en, vn)
    return current_date


def load_build_meta() -> Dict[str, Any]:
    return load_json(META_FILE, {})


def save_build_meta(meta: Dict[str, Any]) -> None:
    save_json(META_FILE, meta)


def check_file_content(file_path: str, llm: ChatNVIDIA, file_hash: Optional[str] = None) -> bool:
    print(f'🔎 Đang kiểm tra sơ bộ nội dung file: {file_path}')

    validation_cache = load_json(VALIDATION_CACHE_FILE, {})
    if file_hash and file_hash in validation_cache:
        cached = validation_cache[file_hash]
        state = 'HỢP LỆ' if cached else 'KHÔNG HỢP LỆ'
        print(f' -> ♻️ Dùng cache kiểm định nội dung: {state}')
        return bool(cached)

    text_sample = ''
    try:
        if file_path.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
            pages = loader.load_and_split()
            if pages:
                text_sample = pages[0].page_content[:1500]
        elif file_path.lower().endswith('.docx'):
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            if docs:
                text_sample = docs[0].page_content[:1500]

        if not text_sample.strip():
            print(' -> ❌ Lỗi: File rỗng hoặc không thể trích xuất chữ.')
            return False
    except Exception as e:
        print(f' -> ❌ Lỗi khi đọc lướt file: {e}')
        return False

    prompt = f'''Bạn là một chuyên gia phân loại tài liệu.
Nhiệm vụ của bạn là đọc đoạn văn bản trích xuất từ một file và xác định xem file này có chứa nội dung liên quan đến "Lịch trình cá nhân", "Thời gian biểu", "Kế hoạch công việc", "Deadline", hoặc "Sự kiện sắp tới" hay không.
Luật phân loại:
1. Trả lời "YES" nếu đoạn văn có dấu hiệu là một lịch trình/kế hoạch.
2. Trả lời "NO" nếu đoạn văn là sách, tài liệu nghiên cứu, truyện, bài báo, hoặc các nội dung không liên quan đến lịch trình cá nhân.
Chỉ trả lời duy nhất 1 từ (YES hoặc NO).
Đoạn văn bản trích xuất:
{text_sample}
'''

    try:
        response = invoke_with_retry(llm, prompt)
        decision = response.content.strip().upper()
        is_valid = 'YES' in decision and 'NO' not in decision

        if 'NO' in decision:
            print(f' -> 🚫 TỪ CHỐI: File không chứa nội dung lịch trình (LLM: {decision}). Hủy bỏ quy trình.')
            is_valid = False
        elif is_valid:
            print(' -> ✅ File hợp lệ (Là tài liệu lịch trình). Cho phép tiến hành xử lý sâu!')
        else:
            print(f' -> ⚠️ LLM trả lời không rõ ràng: {decision}. Từ chối để an toàn.')
            is_valid = False

        if file_hash:
            validation_cache[file_hash] = is_valid
            save_json(VALIDATION_CACHE_FILE, validation_cache)
        return is_valid
    except Exception as e:
        print(f' -> ⚠️ Lỗi khi gọi LLM kiểm định: {e}. Từ chối file để an toàn.')
        return False


def should_rebuild(file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
    file_hash = get_file_hash(file_path)
    meta = load_build_meta()
    today_key = get_today_key()

    if not os.path.exists(DB_DIR):
        return True, file_hash, meta

    required_keys = ['file_hash', 'built_on', 'build_version', 'source_file']
    if not all(k in meta for k in required_keys):
        return True, file_hash, meta

    if meta.get('build_version') != BUILD_VERSION:
        return True, file_hash, meta

    if meta.get('source_file') != SINGLE_FILE_NAME:
        return True, file_hash, meta

    if meta.get('file_hash') != file_hash:
        return True, file_hash, meta

    if meta.get('built_on') != today_key:
        return True, file_hash, meta

    return False, file_hash, meta


def parse_batch_decisions(raw_text: str, expected_count: int) -> List[str]:
    text = raw_text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            decisions = []
            for item in data:
                if isinstance(item, dict):
                    decision = str(item.get('decision', 'KEEP')).upper().strip()
                else:
                    decision = str(item).upper().strip()
                decisions.append('DISCARD' if 'DISCARD' in decision else 'KEEP')
            if len(decisions) == expected_count:
                return decisions
    except Exception:
        pass

    matches = re.findall(r'KEEP|DISCARD', text.upper())
    if len(matches) >= expected_count:
        return matches[:expected_count]

    return ['KEEP'] * expected_count


def classify_chunks_in_batches(chunks: List[Any], current_date_str: str, batch_size: int = 8) -> List[Any]:
    print(f'\n2. Đã bóc tách thành {len(chunks)} đoạn hoàn chỉnh. Bắt đầu lọc sự kiện quá khứ...')
    future_chunks = []
    today_key = get_today_key()
    cache = load_json(CLASSIFY_CACHE_FILE, {})
    llm_filter = create_chat_llm(temperature=0)

    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start:batch_start + batch_size]
        uncached_items = []
        uncached_positions = []
        decisions = [None] * len(batch)

        for i, chunk in enumerate(batch):
            content = chunk.page_content.strip()
            cache_key = f'{today_key}__{hash_text(content)}'
            if cache_key in cache:
                decisions[i] = cache[cache_key]
                print(f' - Đoạn {batch_start + i + 1}: ♻️ dùng cache -> {decisions[i]}')
            else:
                uncached_items.append({'index': i + 1, 'text': content})
                uncached_positions.append(i)

        if uncached_items:
            prompt_parts = [
                f'Hôm nay là ngày {current_date_str}.',
                'Nhiệm vụ của bạn là phân loại từng đoạn văn là KEEP hoặc DISCARD.',
                'Luật phân loại:',
                f'1. Trả lời KEEP nếu đoạn văn chứa lịch trình/sự kiện diễn ra TRONG TƯƠNG LAI (sau ngày {current_date_str}).',
                '2. Trả lời KEEP nếu đoạn văn KHÔNG chứa bất kỳ ngày tháng nào (đây có thể là thông tin chung, nội dung công việc cần giữ lại).',
                f'3. Trả lời DISCARD nếu TẤT CẢ các ngày tháng/sự kiện trong đoạn văn đều đã diễn ra trong QUÁ KHỨ (trước ngày {current_date_str}).',
                '4. Chỉ trả về JSON là một danh sách object theo dạng [{"index": 1, "decision": "KEEP"}, ...].',
                '5. Không giải thích thêm, không thêm markdown.'
            ]

            for item in uncached_items:
                prompt_parts.append(f'\nĐoạn {item["index"]}:\n{item["text"]}')

            prompt = '\n'.join(prompt_parts)
            response = invoke_with_retry(llm_filter, prompt)
            parsed_decisions = parse_batch_decisions(response.content, len(uncached_items))

            for rel_idx, decision in enumerate(parsed_decisions):
                pos = uncached_positions[rel_idx]
                decisions[pos] = decision
                content = batch[pos].page_content.strip()
                cache_key = f'{today_key}__{hash_text(content)}'
                cache[cache_key] = decision

            save_json(CLASSIFY_CACHE_FILE, cache)

        for i, decision in enumerate(decisions):
            final_decision = (decision or 'KEEP').upper().strip()
            chunk_no = batch_start + i + 1
            if 'DISCARD' in final_decision:
                print(f' -> [LOẠI BỎ] Đoạn {chunk_no} vì sự kiện đã qua. (Decision: {final_decision})')
            else:
                print(f' - Đoạn {chunk_no}: [GIỮ LẠI] (Decision: {final_decision})')
                future_chunks.append(batch[i])

        time.sleep(1)

    return future_chunks


def build_vector_database(force_rebuild: bool = False) -> bool:
    file_path = os.path.join(DATA_DIR, SINGLE_FILE_NAME)
    print(f'1. Đang chuẩn bị xử lý file: {file_path}')

    if not os.path.exists(file_path):
        print(f"❌ LỖI: Không tìm thấy file '{file_path}'.")
        return False

    rebuild_needed, file_hash, _ = should_rebuild(file_path)
    if (not force_rebuild) and (not rebuild_needed):
        print('✅ File không thay đổi và DB đã được build trong hôm nay. Bỏ qua rebuild để tiết kiệm API/quota.')
        return True

    try:
        llm_checker = create_chat_llm(temperature=0)
    except Exception as e:
        print(f'❌ LỖI KHỞI TẠO LLM: {e}')
        return False

    is_valid_schedule = check_file_content(file_path, llm_checker, file_hash=file_hash)
    if not is_valid_schedule:
        print('\n🛑 DỪNG CHƯƠNG TRÌNH: Tài liệu không liên quan về lịch trình.')
        return False

    try:
        print('\nBắt đầu đọc, tải và bóc tách cấu trúc (nhận diện bảng)...')
        loader = UnstructuredLoader(
            file_path=file_path,
            partition_via_api=True,
            api_key=os.environ.get('UNSTRUCTURED_API_KEY'),
            strategy='hi_res',
            chunking_strategy='by_title',
            max_characters=1000,
        )
        documents = loader.load()
    except Exception as e:
        print(f'\n❌ Lỗi khi xử lý file {file_path}: {e}')
        return False

    if not documents:
        print('\nKhông thể tải tài liệu từ file. Dừng lại.')
        return False

    current_date_str = datetime.now().strftime('%d/%m/%Y')
    future_chunks = classify_chunks_in_batches(documents, current_date_str=current_date_str, batch_size=8)

    if not future_chunks:
        print('\n⚠️ Không tìm thấy thông tin/sự kiện nào phù hợp. Dừng lại và không lưu vào DB.')
        return False

    print(f'\n3. Đã giữ lại {len(future_chunks)} đoạn. Đang tạo Embeddings & lưu vào ChromaDB...')
    try:
        embeddings = create_embeddings()
    except Exception as e:
        print('\n❌ LỖI KHI KHỞI TẠO NVIDIA EMBEDDINGS:')
        print(f' {e}')
        return False

    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)
    ensure_dir(DB_DIR)

    print('Bắt đầu lưu trữ vào ChromaDB...')
    Chroma.from_documents(
        documents=future_chunks,
        embedding=embeddings,
        persist_directory=DB_DIR,
        collection_name=COLLECTION_NAME,
        collection_metadata={'hnsw:space': 'cosine'}
    )

    save_build_meta({
        'file_hash': file_hash,
        'built_on': get_today_key(),
        'built_at': datetime.now().isoformat(),
        'build_version': BUILD_VERSION,
        'source_file': SINGLE_FILE_NAME,
        'chunk_count': len(future_chunks),
    })

    print('🚀 HOÀN TẤT! Vector Database đã được cập nhật chính xác và sẵn sàng sử dụng.')
    return True


def test_vector_database(query: str, k: int = 4) -> None:
    print(f"\n🔍 Đang hỏi AI: '{query}'...")

    if not os.path.exists(DB_DIR) or not os.path.exists(META_FILE):
        print('❌ Chưa có Vector Database hợp lệ. Hãy build trước.')
        return

    try:
        embeddings = create_embeddings()
        db = Chroma(
            persist_directory=DB_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
            collection_metadata={'hnsw:space': 'cosine'}
        )

        current_date = get_current_date_vn()
        enhanced_query = query
        if needs_temporal_context(query):
            enhanced_query = f'Hôm nay là {current_date}. Câu hỏi của người dùng: {query}'

        results = db.similarity_search(enhanced_query, k=k)
        if not results:
            print(' -> 📭 Database trống hoặc không có kết quả phù hợp.')
            return

        context = '\n\n---\n\n'.join(
            [f'[Đoạn {i + 1}]\n{doc.page_content}' for i, doc in enumerate(results)]
        )

        llm = create_chat_llm(temperature=0.1)
        prompt = f'''Bạn là trợ lý cá nhân thông minh và cực kỳ nguyên tắc.
Hôm nay là {current_date}.
Chỉ được phép trả lời dựa trên dữ liệu có trong phần lịch trình dưới đây. Không dùng kiến thức bên ngoài.

Lịch trình trích xuất từ cơ sở dữ liệu:
{context}

Câu hỏi của người dùng: {query}

LUẬT TRẢ LỜI BẮT BUỘC (ĐỌC KỸ):
1. Bạn phải đối chiếu CHÍNH XÁC từng con số của ngày và tháng.
2. Nếu người dùng hỏi sự kiện ngày hôm nay mà trong lịch trình chỉ có dữ liệu của ngày khác, thì xem là KHÔNG KHỚP.
3. Nếu thông tin người dùng hỏi KHÔNG KHỚP CHÍNH XÁC VỀ NGÀY/THÁNG trong lịch trình, HOẶC nội dung người dùng hỏi không có trong dữ liệu cung cấp, bạn BẮT BUỘC phải trả lời đúng nguyên văn câu sau: "Tôi không tìm thấy thông tin này trong lịch trình của bạn."
4. Tuyệt đối không tự suy diễn, không bịa đặt nội dung.
5. Nếu có thông tin phù hợp, hãy trả lời ngắn gọn, rõ ràng, đúng dữ liệu.
'''

        response = invoke_with_retry(llm, prompt)
        print(f' -> 🤖 AI TRẢ LỜI:\n{response.content}')
    except Exception as e:
        print(f'❌ Lỗi khi truy vấn: {e}')


if __name__ == '__main__':
    build_success = build_vector_database()
    if build_success:
        print('\n' + '=' * 50)
        print('BẮT ĐẦU TEST TRUY VẤN')
        print('=' * 50)
        test_vector_database('Hôm nay có sự kiện gì không?')
        test_vector_database('Khi nào nhóm 4 anh em mình có lịch họp dự án môn Tương tác người máy?')
        test_vector_database('Deadline nộp bản thiết kế UI/UX app giao đồ ăn là ngày mấy?')
