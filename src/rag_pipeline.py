import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

DB_DIR = "./chroma_db"
DATA_DIR = "./data"


def build_vector_database():
    print("1. Đang đọc các file PDF từ thư mục data/...")
    loader = PyPDFDirectoryLoader(DATA_DIR)
    documents = loader.load()

    if not documents:
        print("Không tìm thấy file PDF nào trong thư mục data/!")
        return False

    print(f"2. Đã tải {len(documents)} trang tài liệu. Đang chia nhỏ (Chunking)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)

    print(f"3. Đã chia thành {len(chunks)} đoạn nhỏ. Đang tạo Embeddings & lưu vào ChromaDB...")
    # Sử dụng model đa ngôn ngữ nhẹ, hỗ trợ tiếng Việt tốt
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    # Xóa DB cũ nếu có để cập nhật cái mới
    if os.path.exists(DB_DIR):
        import shutil
        shutil.rmtree(DB_DIR)

    # Lưu vào ChromaDB
    Chroma.from_documents(chunks, embeddings, persist_directory=DB_DIR)

    print("✅ HOÀN TẤT! Vector Database đã sẵn sàng cho AI sử dụng.")
    return True


if __name__ == "__main__":
    build_vector_database()