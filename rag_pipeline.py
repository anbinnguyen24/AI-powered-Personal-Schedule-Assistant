import os
from src.utils.file_utils import get_all_supported_files, get_file_hash, load_json, save_json
from src.utils.llm_utils import create_embeddings
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader
from langchain_chroma import Chroma

DB_DIR = './chroma_db'
DATA_DIR = './data'
REGISTRY_FILE = os.path.join(DB_DIR, 'file_registry.json')


def build_vector_database(force_rebuild: bool = False):
    registry = load_json(REGISTRY_FILE, {})
    all_files = get_all_supported_files(DATA_DIR)
    new_documents = []

    print(f"📂 Tìm thấy {len(all_files)} file.")

    for file_path in all_files:
        file_name = os.path.basename(file_path)
        current_hash = get_file_hash(file_path)

        if not force_rebuild and registry.get(file_name) == current_hash:
            continue

        try:
            # Chọn loader offline tùy theo định dạng file
            if file_path.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file_path.endswith(('.docx', '.doc')):
                # Chạy offline không cần partition_via_api=True
                loader = UnstructuredWordDocumentLoader(file_path)
            else:
                continue

            docs = loader.load()
            new_documents.extend(docs)
            registry[file_name] = current_hash
        except Exception as e:
            print(f"❌ Lỗi xử lý {file_name}: {e}")

    if new_documents:
        embeddings = create_embeddings()
        if force_rebuild and os.path.exists(DB_DIR):
            import shutil
            shutil.rmtree(DB_DIR)

        Chroma.from_documents(
            documents=new_documents,
            embedding=embeddings,
            persist_directory=DB_DIR,
            collection_name='personal_schedule'
        )
        save_json(REGISTRY_FILE, registry)
        return True
    return False