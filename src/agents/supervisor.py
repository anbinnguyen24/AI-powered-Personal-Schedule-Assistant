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
    chain = prompt | llm | StrOutputParser()
    raw_result = chain.invoke({"messages": state["messages"]})

    # Tìm kiếm từ khóa thay vì xóa khoảng trắng
    if "CalendarAgent" in raw_result:
        clean_result = "CalendarAgent"
    elif "ResearchAgent" in raw_result:
        clean_result = "ResearchAgent"
    else:
        clean_result = "FINISH"

    print(f"[Supervisor] Quyết định: {clean_result}")
    return {"next": clean_result}