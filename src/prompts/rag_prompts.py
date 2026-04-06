VALIDATION_PROMPT = """Bạn là chuyên gia phân loại tài liệu. Xác định xem file có liên quan đến "Lịch trình", "Deadline" hay "Kế hoạch" không. Trả lời duy nhất YES hoặc NO.
Nội dung: {text_sample}"""

CLASSIFICATION_PROMPT = """Hôm nay là {current_date}. 
Nhiệm vụ: Trả về JSON danh sách [{"index": i, "decision": "KEEP"|"DISCARD"}] cho các đoạn văn sau.
KEEP nếu là sự kiện tương lai hoặc thông tin chung. DISCARD nếu sự kiện đã qua.
{batch_text}"""

RAG_ANSWER_PROMPT = """Bạn là trợ lý lịch trình. Hôm nay là {current_date}.
Dựa vào dữ liệu sau: {context}
Trả lời câu hỏi: {query}
Nếu không có thông tin chính xác về ngày/tháng, hãy nói: "Tôi không tìm thấy thông tin này trong lịch trình của bạn." """