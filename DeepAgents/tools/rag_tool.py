import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import tool

from DeepAgents.config.settings import CHROMA_DIR

@tool
def search_knowledge_base(query: str) -> str:
    """Tìm kiếm thông tin từ tài liệu PDF/Docx trong cơ sở tri thức (Vector Database).
    Dùng tool này để tra cứu quy chế, tài liệu hướng dẫn, hoặc thông tin tham khảo.

    Args:
        query: Câu hỏi hoặc chủ đề cần tìm kiếm
    """
    try:
        if not os.path.exists(CHROMA_DIR):
            return (
                f"[RAG] Chưa có Vector Database tại {CHROMA_DIR}. "
                "Hãy chạy 'Nạp file PDF vào Vector DB' từ sidebar trước."
            )


        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        docs = vectorstore.similarity_search(query, k=3)

        if not docs:
            return f"[RAG] Không tìm thấy thông tin liên quan đến: '{query}'"

        result = "\n\n".join(
            f"📄 Trích xuất {i + 1}:\n{doc.page_content}"
            for i, doc in enumerate(docs)
        )
        return f"[RAG] Dữ liệu tìm được từ tài liệu:\n{result}"

    except ImportError:
        return "[RAG] Thiếu thư viện (langchain_huggingface hoặc langchain_chroma)."
    except Exception as e:
        return f"[RAG] Lỗi khi truy xuất: {str(e)}"
