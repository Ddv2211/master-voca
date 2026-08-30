"""
Lớp bọc (wrapper) cho Gemini API.

- Đọc API key từ st.secrets["GEMINI_API_KEY"] (khuyến nghị khi deploy lên
  Streamlit Community Cloud: Settings > Secrets) hoặc biến môi trường
  GEMINI_API_KEY (khi chạy local).
- Nếu chưa có key, hoặc gọi API lỗi (hết quota, mất mạng...), MỌI hàm ở
  đây đều rơi về (fallback) một phiên bản tạo bằng template cục bộ, để
  app không bao giờ bị crash chỉ vì thiếu/lỗi Gemini.
- Đổi tên model qua biến môi trường GEMINI_MODEL hoặc st.secrets nếu
  Google đổi tên model trong tương lai (mặc định "gemini-2.5-flash").
"""
from __future__ import annotations

import json
import os
import random
import re

import streamlit as st

_MODEL_CACHE = {}


def _get_api_key() -> str | None:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY")


def _get_model_name() -> str:
    try:
        if "GEMINI_MODEL" in st.secrets:
            return st.secrets["GEMINI_MODEL"]
    except Exception:
        pass
    return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def is_gemini_available() -> bool:
    return _get_api_key() is not None


def _get_model():
    """Khởi tạo (và cache) model Gemini. Trả về None nếu không dùng được."""
    key = _get_api_key()
    if not key:
        return None
    model_name = _get_model_name()
    cache_key = (key[-6:], model_name)
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        _MODEL_CACHE[cache_key] = model
        return model
    except Exception:
        return None


def _clean_json_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json", "", text).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


# --------------------------------------------------------------------------
# 1) Bài tập điền từ vào ngữ cảnh (fill-in-the-blank)
# --------------------------------------------------------------------------

_FALLBACK_TEMPLATES = [
    "The manager asked everyone to ___ before the meeting started.",
    "According to the report, the company plans to ___ next quarter.",
    "Please make sure to ___ the form before submitting it.",
    "Our team needs to ___ in order to meet the deadline.",
    "The client was very satisfied with how we ___ the request.",
]


def generate_fill_blank(word: str, pos: str, meaning: str) -> dict:
    """
    Trả về dict: {"sentence": "... ___ ...", "answer": word,
                  "translation": "bản dịch câu tiếng Việt"}
    """
    model = _get_model()
    if model is not None:
        prompt = (
            f"Tạo 1 câu tiếng Anh trình độ TOEIC (chủ đề công sở/kinh doanh), "
            f"tự nhiên, dùng đúng nghĩa và đúng loại từ của từ '{word}' "
            f"({pos}, nghĩa: {meaning}). Thay từ '{word}' bằng dấu gạch dưới "
            f'"___" trong câu. Chỉ trả JSON: '
            f'{{"sentence": "...", "translation": "bản dịch tiếng Việt của câu đầy đủ"}}'
        )
        try:
            resp = model.generate_content(prompt)
            data = json.loads(_clean_json_text(resp.text))
            if "___" in data.get("sentence", ""):
                return {
                    "sentence": data["sentence"],
                    "answer": word,
                    "translation": data.get("translation", ""),
                }
        except Exception:
            pass

    # Fallback: template đơn giản (không cần Gemini)
    template = random.choice(_FALLBACK_TEMPLATES)
    return {
        "sentence": template,
        "answer": word,
        "translation": "(Chưa kết nối Gemini — không có bản dịch tự động.)",
    }


# --------------------------------------------------------------------------
# 2) Cụm từ / collocation thông dụng đi với 1 từ
# --------------------------------------------------------------------------

def generate_phrases(word: str, pos: str, meaning: str) -> list[dict]:
    """Trả về list [{"phrase": "...", "meaning_vi": "..."}] (3 cụm)."""
    model = _get_model()
    if model is not None:
        prompt = (
            f"Cho từ tiếng Anh '{word}' ({pos}, nghĩa: {meaning}), hãy liệt kê "
            f"3 cụm từ/collocation TOEIC thông dụng nhất có chứa từ này, kèm "
            f'nghĩa tiếng Việt ngắn gọn. Chỉ trả JSON: '
            f'[{{"phrase": "...", "meaning_vi": "..."}}, ...]'
        )
        try:
            resp = model.generate_content(prompt)
            data = json.loads(_clean_json_text(resp.text))
            if isinstance(data, list) and data:
                return data[:3]
        except Exception:
            pass

    return [{"phrase": f"(kết nối Gemini để xem cụm từ với '{word}')",
              "meaning_vi": ""}]


# --------------------------------------------------------------------------
# 3) Tổng kết / nhận xét học tập
# --------------------------------------------------------------------------

def generate_summary_feedback(stats: dict) -> str:
    """
    stats: {"learned": int, "correct": int, "total_quiz": int,
            "weak_words": [word, ...], "topic": str}
    """
    model = _get_model()
    if model is not None:
        prompt = (
            "Bạn là gia sư TOEIC thân thiện. Dựa trên số liệu học tập sau, "
            "hãy viết 1 đoạn nhận xét ngắn (3-4 câu) bằng tiếng Việt, động "
            "viên người học, chỉ ra điểm mạnh và gợi ý cụ thể nên ôn lại từ "
            f"nào: {json.dumps(stats, ensure_ascii=False)}"
        )
        try:
            resp = model.generate_content(prompt)
            if resp.text and resp.text.strip():
                return resp.text.strip()
        except Exception:
            pass

    # Fallback: nhận xét cục bộ dựa trên số liệu
    total = stats.get("total_quiz", 0)
    correct = stats.get("correct", 0)
    acc = round(100 * correct / total) if total else 0
    weak = stats.get("weak_words") or []
    msg = (
        f"Bạn đã học {stats.get('learned', 0)} từ và đạt độ chính xác "
        f"{acc}% trong bài điền từ. "
    )
    if acc >= 80:
        msg += "Rất tốt, bạn đang nắm chắc phần lớn từ vựng! "
    elif acc >= 50:
        msg += "Bạn đã nắm được kha khá, hãy ôn thêm để chắc hơn. "
    else:
        msg += "Nên dành thêm thời gian ôn lại nhóm từ này trước khi học từ mới. "
    if weak:
        msg += f"Chú ý ôn lại: {', '.join(weak[:5])}."
    return msg
