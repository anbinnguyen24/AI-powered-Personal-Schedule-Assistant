import os
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA # Quay lại dùng ChatNVIDIA gốc

load_dotenv()

# Khởi tạo ĐỘNG CƠ DUY NHẤT dùng chung cho toàn bộ hệ thống
shared_llm = ChatNVIDIA(
    model="openai/gpt-oss-20b", 
    temperature=0,
    max_completion_tokens=4192
)