import os
import time
import random
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings, ChatNVIDIA

def create_chat_llm(model='meta/llama-3.1-70b-instruct', temperature=0.0):
    return ChatNVIDIA(
        model=model,
        nvidia_api_key=os.environ.get('NVIDIA_API_KEY'),
        temperature=temperature,
    )

def invoke_with_retry(llm, prompt, max_retries=5):
    for attempt in range(max_retries):
        try:
            return llm.invoke(prompt)
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))
                continue
            raise e