import os
import json
import hashlib

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return default
    return default

def save_json(path: str, data):
    ensure_dir(os.path.dirname(path) or '.')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_file_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''): h.update(chunk)
    return h.hexdigest()