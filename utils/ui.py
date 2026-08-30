"""
Giao diện dùng chung: thanh tiến độ cố định góc trên-trái, menu điều hướng
kiểu "3 gạch -> thả ngang các mục chính -> click mới xổ mục con", và CSS
cho flashcard lật (flip card) để chuyển màn hình mượt mà, liền mạch.
"""
from __future__ import annotations

import streamlit as st

from utils.progress import get_summary_stats

# (Tên hiển thị, key nội bộ) cho từng mục con
MENU = {
    "🃏 Học từ đơn": [
        ("Học theo chủ đề", "topic_picker"),
        ("Học theo nhóm 10 từ", "batch_picker"),
    ],
    "🔤 Cụm từ": [
        ("Cụm từ đã mở khoá", "phrase_learning"),
    ],
    "✍️ Ôn tập": [
        ("Điền từ vào câu", "quiz_entry"),
        ("Ôn lại từ hay sai", "review_weak"),
    ],
    "📊 Tổng kết": [
        ("Thống kê học tập", "dashboard"),
        ("Xuất / Nhập tiến độ", "backup"),
    ],
}


def inject_base_css():
    st.markdown(
        """
        <style>
        /* Ẩn khoảng trắng mặc định phía trên của Streamlit để thanh tiến độ
           nằm sát góc trên-trái, nơi người dùng nhìn vào đầu tiên khi mở tab */
        .block-container { padding-top: 4.5rem !important; }

        .toeic-topbar {
            position: fixed; top: 0; left: 0; right: 0; z-index: 999999;
            background: linear-gradient(90deg, #101828 0%, #1d2b45 100%);
            padding: 10px 18px; display: flex; align-items: center;
            gap: 14px; box-shadow: 0 2px 10px rgba(0,0,0,.15);
        }
        .toeic-progress-wrap { flex: 1; max-width: 420px; }
        .toeic-progress-label {
            color: #cbd5e1; font-size: 12px; margin-bottom: 3px;
            font-family: -apple-system, sans-serif;
        }
        .toeic-progress-track {
            background: rgba(255,255,255,.15); border-radius: 8px; height: 10px;
            overflow: hidden;
        }
        .toeic-progress-fill {
            background: linear-gradient(90deg, #34d399, #22c55e);
            height: 100%; border-radius: 8px; transition: width .5s ease;
        }
        .toeic-xp {
            color: #fbbf24; font-weight: 700; font-size: 13px; white-space: nowrap;
        }

        /* Flashcard */
        .flashcard {
            border-radius: 20px; padding: 46px 30px; text-align: center;
            background: linear-gradient(160deg, #ffffff, #f1f5f9);
            border: 1px solid #e5e7eb; box-shadow: 0 8px 24px rgba(0,0,0,.06);
            min-height: 230px; display: flex; flex-direction: column;
            justify-content: center; animation: fadeIn .35s ease;
        }
        .flashcard.flipped {
            background: linear-gradient(160deg, #ecfdf5, #d1fae5);
        }
        .flashcard-word { font-size: 34px; font-weight: 800; color: #0f172a; }
        .flashcard-phon { color: #64748b; font-style: italic; margin-top: 6px; }
        .flashcard-pos {
            display: inline-block; margin-top: 10px; background: #e0e7ff;
            color: #3730a3; padding: 2px 10px; border-radius: 999px; font-size: 12px;
        }
        .flashcard-meaning { font-size: 26px; font-weight: 700; color: #065f46; }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def top_bar():
    stats = get_summary_stats()
    pct = stats["progress_pct"]
    st.markdown(
        f"""
        <div class="toeic-topbar">
            <div class="toeic-progress-wrap">
                <div class="toeic-progress-label">
                    Hành trình học tập &nbsp;•&nbsp; {stats['learned']}/1000 từ ({pct}%)
                </div>
                <div class="toeic-progress-track">
                    <div class="toeic-progress-fill" style="width:{pct}%;"></div>
                </div>
            </div>
            <div class="toeic-xp">⚡ {stats['xp']} XP</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def go(stage: str, **params):
    st.session_state.stage = stage
    st.session_state.stage_params = params
    st.rerun()


def nav_menu(is_admin: bool = False):
    """Menu: nút ☰ mở hàng ngang các mục chính; click 1 mục chính mới xổ
    hàng mục con bên dưới (không xổ hết tất cả cùng lúc)."""
    menu = dict(MENU)
    if is_admin:
        menu["🛠️ Quản trị"] = [("Quản lý tài khoản", "admin_panel")]

    if "menu_open" not in st.session_state:
        st.session_state.menu_open = False
    if "menu_active_group" not in st.session_state:
        st.session_state.menu_active_group = None

    top_l, top_r = st.columns([1, 11])
    with top_l:
        if st.button("☰", key="hamburger", help="Menu điều hướng"):
            st.session_state.menu_open = not st.session_state.menu_open
            st.session_state.menu_active_group = None

    if st.session_state.menu_open:
        with top_r:
            cols = st.columns(len(menu))
            for col, group_name in zip(cols, menu.keys()):
                with col:
                    active = st.session_state.menu_active_group == group_name
                    if st.button(
                        group_name, key=f"grp_{group_name}",
                        type="primary" if active else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state.menu_active_group = (
                            None if active else group_name
                        )

        active_group = st.session_state.menu_active_group
        if active_group:
            sub_items = menu[active_group]
            sub_cols = st.columns(len(sub_items))
            for col, (label, stage_key) in zip(sub_cols, sub_items):
                with col:
                    if st.button(label, key=f"sub_{stage_key}", use_container_width=True):
                        st.session_state.menu_open = False
                        st.session_state.menu_active_group = None
                        go(stage_key)
    st.divider()
