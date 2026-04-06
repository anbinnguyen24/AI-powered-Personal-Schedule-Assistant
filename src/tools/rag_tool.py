# from langchain_core.tools import tool
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_chroma import Chroma
# import os
#
# DB_DIR = "./chroma_db"
#
# @tool
# def consult_guidelines(query: str) -> str:
#     """Tra cứu thông tin nội bộ, quy định, hoặc tài liệu từ Vector Database."""
#     if not os.path.exists(DB_DIR):
#         return "Lỗi: Chưa có Database. Hãy chạy src/rag_pipeline.py trước."
#     try:
#         embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
#         vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
#         docs = vectorstore.similarity_search(query, k=3)
#         if not docs:
#             return "Không tìm thấy thông tin trong tài liệu."
#         result = "\n\n".join([f"- {doc.page_content}" for doc in docs])
#         return f"Dữ liệu từ tài liệu:\n{result}"
#     except Exception as e:
#         return f"Lỗi truy xuất: {str(e)}"

from langchain_core.tools import tool
from src.utils.llm_utils import create_embeddings
from langchain_chroma import Chroma
import os

DB_DIR = "./chroma_db"

@tool
def consult_guidelines(query: str) -> str:
    """Tra cứu thông tin từ tài liệu cá nhân đã nạp."""
    if not os.path.exists(DB_DIR):
        return "Lỗi: Database chưa sẵn sàng."
    try:
        embeddings = create_embeddings()
        vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
        docs = vectorstore.similarity_search(query, k=3)
        return "\n\n".join([f"- {doc.page_content}" for doc in docs])
    except Exception as e:
        return f"Lỗi: {str(e)}"