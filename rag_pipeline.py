import os
from datetime import datetime
from src.utils.file_utils import get_all_supported_files, get_file_hash, load_json, save_json
from src.utils.llm_utils import create_chat_llm, create_embeddings
from src.prompts.rag_prompts import VALIDATION_PROMPT
from langchain_unstructured import UnstructuredLoader
from langchain_chroma import Chroma

DB_DIR = './chroma_db'
DATA_DIR = './data'
REGISTRY_FILE = os.path.join(DB_DIR, 'file_registry.json')


def build_vector_database(force_rebuild: bool = False):
    # 1. Khởi tạo registry để theo dõi các file đã xử lý
    registry = load_json(REGISTRY_FILE, {})
    all_files = get_all_supported_files(DATA_DIR)

    new_documents = []
    llm = create_chat_llm(temperature=0)

    print(f"📂 Tìm thấy {len(all_files)} file trong thư mục data.")

    for file_path in all_files:
        file_name = os.path.basename(file_path)
        current_hash = get_file_hash(file_path)

        # Kiểm tra xem file đã được xử lý chưa hoặc có thay đổi không
        if not force_rebuild and registry.get(file_name) == current_hash:
            print(f"--- ⏩ Bỏ qua {file_name} (Đã có trong database)")
            continue

        print(f"--- 🔎 Đang xử lý: {file_name}")

        # 2. Kiểm tra nội dung sơ bộ (Sử dụng prompt từ src/prompts/)
        # (Bạn có thể tái sử dụng logic check_file_content hiện có ở đây)

        # 3. Tải và bóc tách dữ liệu
        try:
            loader = UnstructuredLoader(
                file_path=file_path,
                partition_via_api=True,
                strategy='hi_res'
            )
            docs = loader.load()
            new_documents.extend(docs)
            registry[file_name] = current_hash  # Cập nhật registry
        except Exception as e:
            print(f"❌ Lỗi khi xử lý {file_name}: {e}")

    # 4. Lưu vào ChromaDB nếu có dữ liệu mới
    if new_documents:
        print(f"🚀 Đang thêm {len(new_documents)} đoạn văn bản mới vào Vector Database...")
        embeddings = create_embeddings()

        # Nếu force_rebuild, xóa và tạo mới. Nếu không, chỉ thêm vào (add_documents)
        if force_rebuild and os.path.exists(DB_DIR):
            import shutil
            shutil.rmtree(DB_DIR)

        db = Chroma.from_documents(
            documents=new_documents,
            embedding=embeddings,
            persist_directory=DB_DIR,
            collection_name='personal_schedule'
        )

        # Lưu lại trạng thái các file đã xử lý
        save_json(REGISTRY_FILE, registry)
        print("✅ Hoàn tất cập nhật Vector Database.")
    else:
        print("ℹ️ Không có file mới cần cập nhật.")

    return True