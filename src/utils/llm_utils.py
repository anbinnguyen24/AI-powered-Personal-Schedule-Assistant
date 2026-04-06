import os
import time
import random
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings, ChatNVIDIA
import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings


load_dotenv()
# def create_chat_llm(temperature=0.0):
#     return ChatNVIDIA(
#         model='meta/llama-3.1-70b-instruct',
#         nvidia_api_key=os.environ.get('NVIDIA_API_KEY'),
#         temperature=temperature,
#     )

def create_chat_llm(temperature: float = 0.2)-> ChatOpenAI:
    return ChatOpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=os.environ.get('HF_TOKEN'),
        model="Qwen/Qwen2.5-72B-Instruct",
        temperature=temperature,
    )

# def create_embeddings():
#     return NVIDIAEmbeddings(
#         model='nvidia/nv-embed-v1',
#         nvidia_api_key=os.environ.get('NVIDIA_API_KEY')
#     )

def create_embeddings():
    # Sử dụng model đa ngôn ngữ chạy local (không cần API Key cho phần này)
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

def invoke_with_retry(llm, prompt, max_retries=6):
    for attempt in range(max_retries):
        try:
            return llm.invoke(prompt)
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))
                continue
            raise e