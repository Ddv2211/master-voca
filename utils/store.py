"""
Lưu tiến độ học của TỪNG TÀI KHOẢN lên Google Sheets — để khi người dùng
đăng nhập lại (ở máy khác, hay sau khi app bị khởi động lại trên
Streamlit Cloud), họ KHÔNG phải học lại từ đầu.

Vì sao chọn Google Sheets thay vì lưu file cục bộ?
Streamlit Community Cloud không có ổ đĩa vĩnh viễn — file ghi ra trong
lúc app chạy sẽ mất khi app được deploy lại / khởi động lại. Google
Sheets là một "database" đơn giản, miễn phí, đọc/ghi được từ Python qua
`gspread`, và BẠN (admin) có thể mở trực tiếp Sheet đó để xem dữ liệu.

Cấu trúc 1 Google Sheet, 1 worksheet tên "progress", các cột:
    username | banned | updated_at | progress_json

Nếu CHƯA cấu hình Google Sheets trong Secrets, mọi hàm ở đây sẽ tự động
vô hiệu hoá (is_enabled() = False) và app vẫn chạy bình thường — chỉ là
tiến độ sẽ không được đồng bộ lên "đám mây", chỉ lưu tạm trong phiên
làm việc (giống hành vi trước khi có tính năng đăng nhập).
"""
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

WORKSHEET_NAME = "progress"
HEADER = ["username", "banned", "updated_at", "progress_json"]


def is_enabled() -> bool:
    try:
        return "gcp_service_account" in st.secrets and "sheets" in st.secrets
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _client():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)


def _worksheet():
    gc = _client()
    sheet_id = st.secrets["sheets"]["spreadsheet_id"]
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except Exception:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=200, cols=len(HEADER))
        ws.append_row(HEADER)
    if ws.row_values(1) != HEADER:
        ws.update("A1", [HEADER])
    return ws


def _find_row(ws, username: str):
    try:
        cell = ws.find(username, in_column=1)
        return cell.row if cell else None
    except Exception:
        return None


def load_user_row(username: str) -> dict | None:
    """Trả về {"banned": bool, "updated_at": str, "progress": dict} hoặc None."""
    if not is_enabled():
        return None
    try:
        ws = _worksheet()
        row_num = _find_row(ws, username)
        if not row_num:
            return None
        row = ws.row_values(row_num)
        row += [""] * (len(HEADER) - len(row))
        banned = str(row[1]).strip().upper() == "TRUE"
        progress = json.loads(row[3]) if row[3] else None
        return {"banned": banned, "updated_at": row[2], "progress": progress}
    except Exception as e:
        st.session_state["_store_error"] = str(e)
        return None


def save_user_row(username: str, progress_dict: dict, banned: bool = False):
    if not is_enabled():
        return False
    try:
        ws = _worksheet()
        row_num = _find_row(ws, username)
        values = [
            username, "TRUE" if banned else "FALSE",
            datetime.now().isoformat(timespec="seconds"),
            json.dumps(progress_dict, ensure_ascii=False),
        ]
        if row_num:
            ws.update(f"A{row_num}:D{row_num}", [values])
        else:
            ws.append_row(values)
        return True
    except Exception as e:
        st.session_state["_store_error"] = str(e)
        return False


def set_banned(username: str, banned: bool) -> bool:
    if not is_enabled():
        return False
    try:
        ws = _worksheet()
        row_num = _find_row(ws, username)
        if not row_num:
            return False
        ws.update_cell(row_num, 2, "TRUE" if banned else "FALSE")
        return True
    except Exception as e:
        st.session_state["_store_error"] = str(e)
        return False


def list_all_users() -> list[dict]:
    """Dùng cho trang Quản trị: đọc toàn bộ tài khoản đã từng đăng nhập."""
    if not is_enabled():
        return []
    try:
        ws = _worksheet()
        records = ws.get_all_records()
        out = []
        for r in records:
            try:
                progress = json.loads(r.get("progress_json") or "{}")
            except Exception:
                progress = {}
            out.append({
                "username": r.get("username", ""),
                "banned": str(r.get("banned", "")).strip().upper() == "TRUE",
                "updated_at": r.get("updated_at", ""),
                "progress": progress,
            })
        return out
    except Exception as e:
        st.session_state["_store_error"] = str(e)
        return []
