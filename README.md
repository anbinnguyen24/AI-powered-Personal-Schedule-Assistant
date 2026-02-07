# AI-powered-Personal-Schedule-Assistant

[![Code](https://img.shields.io/badge/GitHub-Repository-black)](https://github.com/anbinnguyen24/AI-powered-Personal-Schedule-Assistant)
[![LLM](https://img.shields.io/badge/LLM-Qwen3--235B-orange)](https://huggingface.co/Qwen/Qwen3-235B-A22B)

## 📖 Introduction
Xây dựng AI Agent đề xuất lịch trình cá nhân sử dụng framework LangChain kết hợp vơi RAG và mô hình ngôn ngữ lớn Qwen

Để chạy dự án này, bạn cần thiết lập các biến môi trường trong file `.env` như sau:

```env
HF_TOKEN=your_huggingface_token_here
```

Thay `your_huggingface_token_here` bằng token thực tế của bạn từ [Hugging Face Tokens](https://huggingface.co/settings/tokens).

## Cài đặt
Để cài đặt các phụ thuộc cần thiết, bạn có thể sử dụng pip:

```bash
pip install -r requirements.txt
```

## Sử dụng
Chạy file `frontend1.py` để khởi động dự án:

```bash
streamlit run frontend1.py
```
