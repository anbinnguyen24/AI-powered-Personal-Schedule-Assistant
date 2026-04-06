from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel
from typing import Literal
from langchain_core.output_parsers import StrOutputParser
from src.prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from src.utils.llm_utils import create_chat_llm

# Định nghĩa các hướng đi
options = ["FINISH", "CalendarAgent", "ResearchAgent"]

class Route(BaseModel):
    next: Literal["FINISH", "CalendarAgent", "ResearchAgent"]

def supervisor_node(state, llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
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