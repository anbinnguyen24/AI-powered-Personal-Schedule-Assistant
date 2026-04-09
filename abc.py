from langchain_unstructured import UnstructuredLoader

# Tạo file mẫu
sample_text = """
LangChain là framework hỗ trợ xây dựng ứng dụng với mô hình ngôn ngữ lớn.

Unstructured API giúp tách nội dung từ tài liệu và trả về các document có metadata.

Khi kết hợp LangChain với Unstructured API, chúng ta có thể đọc tài liệu,
biến tài liệu thành Document, rồi dùng tiếp cho RAG hoặc chatbot hỏi đáp tài liệu.
"""

file_path = "demo_unstructured_api.txt"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(sample_text)

# Dùng Unstructured API (không local)
loader = UnstructuredLoader(
    file_path=file_path,
    partition_via_api=True,
    strategy="fast",
    chunking_strategy="basic",
)

docs = loader.load()

print("✅ Số lượng docs:", len(docs))

print("\n" + "="*70)
print("1) DOCUMENT ĐẦU TIÊN")
print("="*70)
print(docs[0])

print("\n" + "="*70)
print("2) NỘI DUNG + METADATA")
print("="*70)
for i, doc in enumerate(docs, 1):
    print(f"\n--- Document {i} ---")
    print("Nội dung :", doc.page_content[:500])
    print("Metadata :", doc.metadata)