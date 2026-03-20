# File: src/tools/rag_tool.py
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

DB_DIR = "./chroma_db"


@tool
def consult_guidelines(query: str) -> str:
    try:
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)

        # Tìm 5 đoạn văn bản liên quan nhất
        docs = vectorstore.similarity_search(query, k=5)

        if not docs:
            return "Không tìm thấy quy định nào liên quan trong tài liệu nội bộ."

        result = "\n\n".join([f"Trích xuất {i + 1}:\n{doc.page_content}" for i, doc in enumerate(docs)])
        return f"Dữ liệu tìm thấy từ tài liệu (Hãy dựa vào đây để tư vấn):\n{result}"
    except Exception as e:
        return f"Lỗi khi truy xuất tài liệu: {str(e)}"