from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel
from typing import Literal
from langchain_core.output_parsers import StrOutputParser

# Định nghĩa các hướng đi
options = ["FINISH", "CalendarAgent", "ResearchAgent"]

class Route(BaseModel):
    next: Literal["FINISH", "CalendarAgent", "ResearchAgent"]

# def supervisor_node(state, llm):
#     system_prompt = (
#         "Bạn là Quản lý điều phối. Hãy đọc tin nhắn cuối cùng và quyết định ai làm tiếp:\n"
#         "- Lịch trình, thời gian, nhắc nhở -> Chọn 'CalendarAgent'\n"
#         "- Tìm kiếm thông tin, hỏi kiến thức, đọc tài liệu -> Chọn 'ResearchAgent'\n"
#         "- Nếu là lời chào bình thường hoặc công việc đã xong -> Chọn 'FINISH'\n"
#     )
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", system_prompt),
#         MessagesPlaceholder(variable_name="messages"),
#         ("system", "Ai sẽ xử lý tiếp theo?")
#     ])
#
#     # Ép LLM trả về đúng 1 trong 3 giá trị, ngăn chặn lỗi logic
#     supervisor_chain = prompt | llm.with_structured_output(Route)
#     result = supervisor_chain.invoke({"messages": state["messages"]})
#
#     print(f"[Supervisor] Quyết định: {result.next}")
#     return {"next": result.next}

def supervisor_node(state, llm):
    # Thay đổi System Prompt để ép LLM chỉ trả về đúng 1 từ duy nhất
    system_prompt = (
        "Bạn là Quản lý điều phối. Hãy đọc tin nhắn cuối cùng và quyết định ai làm tiếp:\n"
        "- Nếu yêu cầu về Lịch trình, thời gian, nhắc nhở -> Trả về đúng chữ: CalendarAgent\n"
        "- Nếu yêu cầu Tìm kiếm thông tin, hỏi kiến thức, đọc tài liệu -> Trả về đúng chữ: ResearchAgent\n"
        "- Nếu là lời chào bình thường hoặc công việc đã giải quyết xong -> Trả về đúng chữ: FINISH\n"
        "\nTUYỆT ĐỐI CHỈ TRẢ VỀ 1 TRONG 3 TỪ TRÊN. KHÔNG GIẢI THÍCH THÊM BẤT CỨ ĐIỀU GÌ."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Ai sẽ xử lý tiếp theo? Chỉ in ra tên Agent.")
    ])

    # Sử dụng StrOutputParser để lấy chuỗi văn bản thuần túy thay vì Structured Output
    chain = prompt | llm | StrOutputParser()
    raw_result = chain.invoke({"messages": state["messages"]})

    # Làm sạch dữ liệu (Xóa khoảng trắng, dấu nháy nếu LLM lỡ sinh ra)
    clean_result = raw_result.strip().strip("'\"").replace(" ", "")

    # Fallback an toàn
    valid_options = ["CalendarAgent", "ResearchAgent", "FINISH"]
    if clean_result not in valid_options:
        print(f"[Supervisor] Model trả về sai format: '{clean_result}'. Mặc định chọn FINISH.")
        clean_result = "FINISH"

    print(f"[Supervisor] Quyết định: {clean_result}")
    return {"next": clean_result}