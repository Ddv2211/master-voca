"""
Theo dõi tiến độ học tập.

Lưu trong st.session_state khi đang chạy (không mất khi chuyển màn hình
trong cùng phiên). Ngoài ra cho phép Xuất / Nhập tiến độ ra file .json để
người dùng tự lưu lại — vì Streamlit Community Cloud là hosting "ephemeral"
(dữ liệu ghi ra đĩa sẽ mất khi ứng dụng khởi động lại), nên đây là cách
đơn giản, đáng tin cậy nhất để không mất tiến độ giữa các lần học nếu
không tự dựng thêm cơ sở dữ liệu (xem README phần "Nâng cấp tương lai").
"""
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from utils import store

DEFAULT_STATE = {
    "learned_stts": [],        # các từ đơn đã học flashcard (list[int])
    "mastered_stts": [],       # các từ đã làm đúng bài điền từ (list[int])
    "phrase_learned_stts": [], # các từ đã học xong cụm từ liên quan
    "quiz_log": [],            # [{"stt": int, "word": str, "correct": bool, "ts": str}]
    "xp": 0,
    "streak_days": 1,
    "last_active_date": None,
}


def init_progress():
    if "progress" not in st.session_state:
        st.session_state.progress = json.loads(json.dumps(DEFAULT_STATE))

    today = datetime.now().strftime("%Y-%m-%d")
    p = st.session_state.progress
    if p.get("last_active_date") != today:
        p["last_active_date"] = today


def hydrate_from_remote(remote_progress: dict | None):
    """Gộp tiến độ tải từ Google Sheets vào session hiện tại — chỉ nên
    gọi 1 lần ngay sau khi đăng nhập thành công."""
    if not remote_progress:
        return
    merged = json.loads(json.dumps(DEFAULT_STATE))
    merged.update(remote_progress)
    st.session_state.progress = merged


def _sync_to_cloud():
    username = st.session_state.get("username")
    if username and store.is_enabled():
        store.save_user_row(username, st.session_state.progress)


def mark_learned(stt: int):
    p = st.session_state.progress
    if stt not in p["learned_stts"]:
        p["learned_stts"].append(stt)
        p["xp"] += 5
    _sync_to_cloud()


def mark_phrase_learned(stt: int):
    p = st.session_state.progress
    if stt not in p["phrase_learned_stts"]:
        p["phrase_learned_stts"].append(stt)
        p["xp"] += 3
    _sync_to_cloud()


def record_quiz_result(stt: int, word: str, correct: bool):
    p = st.session_state.progress
    p["quiz_log"].append({
        "stt": stt, "word": word, "correct": correct,
        "ts": datetime.now().isoformat(timespec="seconds"),
    })
    if correct:
        p["xp"] += 10
        if stt not in p["mastered_stts"]:
            p["mastered_stts"].append(stt)
    _sync_to_cloud()


def get_weak_words(limit: int = 5) -> list[str]:
    """Từ hay bị sai nhất trong bài điền từ, dựa trên log gần đây."""
    p = st.session_state.progress
    wrong_counts: dict[str, int] = {}
    for entry in p["quiz_log"]:
        if not entry["correct"]:
            wrong_counts[entry["word"]] = wrong_counts.get(entry["word"], 0) + 1
    ranked = sorted(wrong_counts.items(), key=lambda x: -x[1])
    return [w for w, _ in ranked[:limit]]


def get_summary_stats(total_vocab: int = 1000) -> dict:
    p = st.session_state.progress
    total_quiz = len(p["quiz_log"])
    correct = sum(1 for e in p["quiz_log"] if e["correct"])
    return {
        "learned": len(p["learned_stts"]),
        "mastered": len(p["mastered_stts"]),
        "phrase_learned": len(p["phrase_learned_stts"]),
        "total_quiz": total_quiz,
        "correct": correct,
        "accuracy": round(100 * correct / total_quiz) if total_quiz else 0,
        "weak_words": get_weak_words(),
        "xp": p["xp"],
        "progress_pct": round(100 * len(p["learned_stts"]) / total_vocab, 1),
    }


def export_progress() -> str:
    return json.dumps(st.session_state.progress, ensure_ascii=False, indent=1)


def import_progress(raw_json: str) -> bool:
    try:
        data = json.loads(raw_json)
        merged = json.loads(json.dumps(DEFAULT_STATE))
        merged.update(data)
        st.session_state.progress = merged
        return True
    except Exception:
        return False
