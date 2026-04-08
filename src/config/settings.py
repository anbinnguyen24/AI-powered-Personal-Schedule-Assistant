import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

load_dotenv()

# ── Biến môi trường ──────────────────────────────────────────
HF_TOKEN: str = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    raise ValueError("Chưa tìm thấy HF_TOKEN trong file .env!")

# ── Đường dẫn dữ liệu ───────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")

# ── Thời gian hiện tại ───────────────────────────────────────
NOW = datetime.now()
CURRENT_TIME_STR = NOW.strftime("%A, ngày %d tháng %m năm %Y, lúc %H:%M")

# ── Sandbox toggle ────────────────────────────────────────────
ENABLE_SANDBOX: bool = os.environ.get("ENABLE_SANDBOX", "false").lower() == "true"


def get_llm(temperature: float = 0.2)-> ChatOpenAI:
    return ChatOpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=HF_TOKEN,
        model="Qwen/Qwen2.5-72B-Instruct",
        temperature=temperature,
    )


# def get_llm(temperature: float = 0.2) -> ChatOllama:
#     return ChatOllama(
#         model="qwen2.5:7b",
#         temperature=temperature,
#     )
