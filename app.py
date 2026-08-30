import random

import streamlit as st

from utils import auth
from utils import data_loader as dl
from utils import gemini_client as gc
from utils import progress as pg
from utils import store
from utils import tts
from utils import ui

st.set_page_config(
    page_title="TOEIC 1000 - Học từ vựng thông minh",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---- 1) Đăng nhập (bắt buộc — không có tự đăng ký) ----
authenticator, username, display_name, roles = auth.login_gate()
is_admin = auth.is_admin(roles)

# ---- 2) Kiểm tra tài khoản có bị quản trị viên khoá không ----
_remote = store.load_user_row(username) if store.is_enabled() else None
if _remote and _remote.get("banned"):
    st.error("🚫 Tài khoản của bạn đã bị quản trị viên khoá quyền truy cập.")
    authenticator.logout("Đăng xuất", "main")
    st.stop()

pg.init_progress()
if not st.session_state.get("_progress_hydrated"):
    if _remote and _remote.get("progress"):
        pg.hydrate_from_remote(_remote["progress"])
    st.session_state["_progress_hydrated"] = True

ui.inject_base_css()
ui.top_bar()

hello_col, logout_col = st.columns([6, 1])
with hello_col:
    st.caption(f"👋 Xin chào, **{display_name or username}**" + (" · 🛠️ Quản trị viên" if is_admin else ""))
with logout_col:
    authenticator.logout("Đăng xuất", "main", use_container_width=True)

ui.nav_menu(is_admin=is_admin)

if "stage" not in st.session_state:
    st.session_state.stage = "home"
if "stage_params" not in st.session_state:
    st.session_state.stage_params = {}


# =============================================================================
# HOME
# =============================================================================
def render_home():
    st.markdown("## 👋 Chào mừng bạn quay lại!")
    stats = pg.get_summary_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Từ đã học", stats["learned"])
    c2.metric("Từ đã thuộc (quiz đúng)", stats["mastered"])
    c3.metric("Độ chính xác điền từ", f"{stats['accuracy']}%")
    c4.metric("Điểm XP", stats["xp"])

    st.markdown("---")
    st.markdown("### Bắt đầu nhanh")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**🃏 Học theo nhóm 10 từ (theo thứ tự sách)**")
        if st.button("Bắt đầu học →", key="quick_batch", use_container_width=True):
            ui.go("batch_picker")
    with col2:
        st.markdown("**🗂️ Học theo chủ đề quen thuộc**")
        if st.button("Chọn chủ đề →", key="quick_topic", use_container_width=True):
            ui.go("topic_picker")
    with col3:
        st.markdown("**🧠 Ôn lại từ hay sai**")
        if st.button("Ôn tập ngay →", key="quick_review", use_container_width=True):
            ui.go("review_weak")

    if not gc.is_gemini_available():
        st.info(
            "💡 Chưa kết nối Gemini API — app vẫn hoạt động với câu ví dụ mẫu có "
            "sẵn. Thêm `GEMINI_API_KEY` vào Settings → Secrets để có câu ví dụ "
            "và cụm từ được Gemini tạo riêng cho từng từ.",
            icon="💡",
        )


# =============================================================================
# CHỌN CHỦ ĐỀ / CHỌN NHÓM 10 TỪ
# =============================================================================
def render_topic_picker():
    st.markdown("## 🗂️ Chọn chủ đề để học")
    topics = dl.get_topics()
    cols = st.columns(3)
    for i, topic in enumerate(topics):
        words = dl.words_by_topic(topic)
        learned = len(
            [w for w in words if w["stt"] in st.session_state.progress["learned_stts"]]
        )
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{topic}**")
                st.caption(f"{learned}/{len(words)} từ đã học")
                st.progress(learned / len(words) if words else 0)
                if st.button("Học chủ đề này", key=f"topic_{topic}", use_container_width=True):
                    start_flashcard_session(words, source_label=topic)


def render_batch_picker():
    st.markdown("## 🔢 Chọn nhóm 10 từ (theo đúng thứ tự trong sách)")
    batches = dl.get_batches()
    learned_set = set(st.session_state.progress["learned_stts"])

    default_batch = 1
    for b in batches:
        words = dl.words_by_batch(b)
        if not all(w["stt"] in learned_set for w in words):
            default_batch = b
            break

    batch = st.selectbox(
        "Nhóm từ", batches,
        index=batches.index(default_batch),
        format_func=lambda b: f"Nhóm {b}  (từ #{(b-1)*10+1} → #{b*10})",
    )
    words = dl.words_by_batch(batch)
    st.write(", ".join(f"**{w['word']}**" for w in words))
    if st.button("Bắt đầu học nhóm này →", type="primary"):
        start_flashcard_session(words, source_label=f"Nhóm {batch}")


def start_flashcard_session(words, source_label):
    st.session_state.session_words = words
    st.session_state.session_label = source_label
    st.session_state.flash_idx = 0
    st.session_state.flash_flipped = False
    st.session_state.session_newly_learned = []
    ui.go("flashcard")


# =============================================================================
# FLASHCARD
# =============================================================================
def render_flashcard():
    words = st.session_state.get("session_words")
    if not words:
        st.warning("Chưa chọn nhóm từ nào. Hãy chọn chủ đề hoặc nhóm từ trước.")
        if st.button("← Quay lại"):
            ui.go("home")
        return

    idx = st.session_state.flash_idx
    total = len(words)

    if idx >= total:
        st.success(f"🎉 Bạn đã học xong {total} từ trong **{st.session_state.session_label}**!")
        st.balloons()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✍️ Làm bài điền từ ngay →", type="primary", use_container_width=True):
                ui.go("quiz_entry")
        with c2:
            if st.button("🏠 Về trang chủ", use_container_width=True):
                ui.go("home")
        return

    word = words[idx]
    st.markdown(f"#### {st.session_state.session_label} · Thẻ {idx + 1}/{total}")
    st.progress((idx) / total)

    flipped = st.session_state.flash_flipped
    card_class = "flashcard flipped" if flipped else "flashcard"
    if not flipped:
        st.markdown(
            f"""<div class="{card_class}">
                    <div class="flashcard-word">{word['word']}</div>
                    <div class="flashcard-phon">{word['phonetic']}</div>
                    <div><span class="flashcard-pos">{word['pos']}</span></div>
                </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""<div class="{card_class}">
                    <div class="flashcard-meaning">{word['meaning']}</div>
                    <div class="flashcard-phon">{word['word']} · {word['phonetic']}</div>
                </div>""",
            unsafe_allow_html=True,
        )

    auto_speak = st.session_state.get("auto_speak", False)
    speak_col, toggle_col = st.columns([2, 3])
    with speak_col:
        tts.speak_button(
            word["word"],
            key=f"speak_{word['stt']}_{flipped}",
            autoplay=auto_speak,
        )
    with toggle_col:
        st.session_state.auto_speak = st.checkbox(
            "🔊 Tự động phát âm khi hiện thẻ mới",
            value=auto_speak,
            key="auto_speak_toggle",
        )

    st.write("")
    b1, b2, b3 = st.columns([1, 1, 1])
    with b1:
        if st.button("🔄 Lật thẻ", use_container_width=True):
            st.session_state.flash_flipped = not flipped
            st.rerun()
    with b2:
        if st.button("😕 Cần ôn thêm", use_container_width=True):
            st.session_state.flash_idx += 1
            st.session_state.flash_flipped = False
            st.rerun()
    with b3:
        if st.button("✅ Đã thuộc", type="primary", use_container_width=True):
            pg.mark_learned(word["stt"])
            st.session_state.session_newly_learned.append(word)
            st.session_state.flash_idx += 1
            st.session_state.flash_flipped = False
            st.rerun()


# =============================================================================
# QUIZ — ĐIỀN TỪ VÀO NGỮ CẢNH
# =============================================================================
def build_quiz_questions(words):
    all_words = dl.load_vocabulary()
    questions = []
    for w in words:
        with st.spinner(f"Đang tạo câu ví dụ cho '{w['word']}'..."):
            gen = gc.generate_fill_blank(w["word"], w["pos"], w["meaning"])
        same_pos = [x for x in all_words if x["pos"] == w["pos"] and x["stt"] != w["stt"]]
        pool = same_pos if len(same_pos) >= 3 else all_words
        distractors = random.sample(
            [x["word"] for x in pool if x["word"] != w["word"]], k=3
        )
        options = distractors + [w["word"]]
        random.shuffle(options)
        questions.append({
            "stt": w["stt"], "word": w["word"], "meaning": w["meaning"],
            "sentence": gen["sentence"], "translation": gen.get("translation", ""),
            "options": options,
        })
    return questions


def render_quiz_entry():
    words = st.session_state.get("session_newly_learned") or st.session_state.get("session_words")
    if not words:
        st.warning("Chưa có từ nào để làm bài điền từ. Hãy học flashcard trước.")
        if st.button("← Về trang chủ"):
            ui.go("home")
        return

    if "quiz_questions" not in st.session_state or st.session_state.get("quiz_source") != id(words):
        st.session_state.quiz_questions = build_quiz_questions(words)
        st.session_state.quiz_source = id(words)
        st.session_state.quiz_idx = 0
        st.session_state.quiz_answered = False
        st.session_state.quiz_selected = None

    ui.go("quiz_run")


def render_quiz_run():
    questions = st.session_state.get("quiz_questions", [])
    idx = st.session_state.get("quiz_idx", 0)

    if not questions:
        ui.go("quiz_entry")
        return

    if idx >= len(questions):
        correct_n = sum(1 for q in questions if q.get("was_correct"))
        st.success(f"Hoàn thành bài điền từ! Đúng {correct_n}/{len(questions)} câu.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔤 Học cụm từ với các từ này →", type="primary", use_container_width=True):
                st.session_state.phrase_words = [
                    w for w in st.session_state.session_words
                ]
                st.session_state.phrase_idx = 0
                ui.go("phrase_learning")
        with c2:
            if st.button("📊 Xem tổng kết", use_container_width=True):
                ui.go("dashboard")
        return

    q = questions[idx]
    st.markdown(f"#### ✍️ Điền từ vào câu · Câu {idx + 1}/{len(questions)}")
    st.progress(idx / len(questions))

    sentence_display = q["sentence"].replace("___", "**\\_\\_\\_\\_\\_\\_**")
    st.markdown(f"### {sentence_display}")
    if q.get("translation"):
        st.caption(f"Gợi ý nghĩa câu: {q['translation']}")

    answered = st.session_state.get("quiz_answered", False)
    cols = st.columns(4)
    for i, opt in enumerate(q["options"]):
        with cols[i]:
            disabled = answered
            if st.button(opt, key=f"opt_{idx}_{opt}", use_container_width=True, disabled=disabled):
                is_correct = opt == q["word"]
                q["was_correct"] = is_correct
                pg.record_quiz_result(q["stt"], q["word"], is_correct)
                st.session_state.quiz_answered = True
                st.session_state.quiz_selected = opt
                st.rerun()

    if answered:
        selected = st.session_state.quiz_selected
        if selected == q["word"]:
            st.success(f"✅ Chính xác! **{q['word']}** — {q['meaning']}")
        else:
            st.error(f"❌ Chưa đúng. Đáp án là **{q['word']}** — {q['meaning']}")
        if st.button("Câu tiếp theo →", type="primary"):
            st.session_state.quiz_idx += 1
            st.session_state.quiz_answered = False
            st.session_state.quiz_selected = None
            st.rerun()


# =============================================================================
# HỌC CỤM TỪ (sau khi thuộc từ đơn)
# =============================================================================
def render_phrase_learning():
    words = st.session_state.get("phrase_words") or st.session_state.get("session_words")
    if not words:
        st.warning("Chưa có từ nào để học cụm từ. Hãy học từ đơn trước.")
        if st.button("← Về trang chủ"):
            ui.go("home")
        return

    idx = st.session_state.get("phrase_idx", 0)
    if idx >= len(words):
        st.success("🎉 Bạn đã học xong cụm từ cho toàn bộ nhóm từ này!")
        if st.button("📊 Xem tổng kết buổi học →", type="primary"):
            ui.go("dashboard")
        return

    w = words[idx]
    st.markdown(f"#### 🔤 Cụm từ thông dụng · {idx + 1}/{len(words)}")
    st.markdown(f"### {w['word']} ({w['pos']}) — {w['meaning']}")

    cache_key = f"phrases_{w['stt']}"
    if cache_key not in st.session_state:
        with st.spinner("Đang tạo cụm từ liên quan..."):
            st.session_state[cache_key] = gc.generate_phrases(w["word"], w["pos"], w["meaning"])
    phrases = st.session_state[cache_key]

    for p in phrases:
        with st.container(border=True):
            st.markdown(f"**{p['phrase']}**")
            if p.get("meaning_vi"):
                st.caption(p["meaning_vi"])

    if st.button("Đã ghi nhớ, tiếp tục →", type="primary"):
        pg.mark_phrase_learned(w["stt"])
        st.session_state.phrase_idx += 1
        st.rerun()


# =============================================================================
# ÔN TẬP TỪ HAY SAI
# =============================================================================
def render_review_weak():
    weak_words_names = pg.get_weak_words(limit=20)
    if not weak_words_names:
        st.info("Bạn chưa có từ nào bị sai trong bài điền từ — chưa cần ôn tập riêng! 🎉")
        if st.button("← Về trang chủ"):
            ui.go("home")
        return
    all_words = dl.load_vocabulary()
    words = [w for w in all_words if w["word"] in weak_words_names]
    st.markdown("## 🧠 Ôn lại các từ bạn hay nhầm")
    st.caption(f"{len(words)} từ được chọn dựa trên lịch sử làm bài điền từ của bạn.")
    if st.button("Bắt đầu ôn tập →", type="primary"):
        start_flashcard_session(words, source_label="Ôn tập từ hay sai")


# =============================================================================
# TỔNG KẾT / DASHBOARD
# =============================================================================
def render_dashboard():
    st.markdown("## 📊 Tổng kết quá trình học tập")
    stats = pg.get_summary_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng số từ đã học", stats["learned"])
    c2.metric("Số câu điền từ đã làm", stats["total_quiz"])
    c3.metric("Độ chính xác", f"{stats['accuracy']}%")
    c4.metric("Điểm kinh nghiệm (XP)", stats["xp"])

    st.progress(stats["progress_pct"] / 100, text=f"Tiến độ tổng: {stats['progress_pct']}% / 1000 từ")

    with st.spinner("Đang tạo nhận xét học tập..."):
        feedback = gc.generate_summary_feedback(stats)
    st.info(feedback, icon="🎯")

    if stats["weak_words"]:
        st.markdown("#### ⚠️ Những từ nên ôn lại")
        st.write(", ".join(f"`{w}`" for w in stats["weak_words"]))
        if st.button("Ôn tập ngay các từ này →"):
            ui.go("review_weak")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🃏 Học tiếp nhóm từ mới →", type="primary", use_container_width=True):
            ui.go("batch_picker")
    with c2:
        if st.button("💾 Sao lưu tiến độ →", use_container_width=True):
            ui.go("backup")


def render_backup():
    st.markdown("## 💾 Xuất / Nhập tiến độ học tập")
    st.caption(
        "App chạy trên Streamlit Community Cloud không lưu dữ liệu vĩnh viễn — "
        "hãy tải file tiến độ về máy sau mỗi buổi học, và nhập lại khi quay lại lần sau."
    )
    st.download_button(
        "⬇️ Tải file tiến độ (.json)",
        data=pg.export_progress(),
        file_name="toeic_progress.json",
        mime="application/json",
    )
    uploaded = st.file_uploader("⬆️ Nhập lại tiến độ từ file .json", type=["json"])
    if uploaded is not None:
        content = uploaded.read().decode("utf-8")
        if pg.import_progress(content):
            st.success("Đã khôi phục tiến độ thành công!")
            st.rerun()
        else:
            st.error("File không hợp lệ.")


def render_admin_panel():
    st.markdown("## 🛠️ Quản lý tài khoản")
    if not store.is_enabled():
        st.warning(
            "Chưa cấu hình Google Sheets nên chưa có dữ liệu hoạt động của các "
            "tài khoản để hiển thị ở đây. Xem README.md phần 'Đăng nhập & quản "
            "lý tài khoản' để bật tính năng này.",
            icon="⚠️",
        )
        return

    if st.session_state.get("_store_error"):
        st.error(f"Lỗi kết nối Google Sheets: {st.session_state['_store_error']}")

    if st.button("🔄 Làm mới danh sách"):
        st.rerun()

    users = store.list_all_users()
    if not users:
        st.info("Chưa có tài khoản nào đăng nhập lần nào.")
        return

    st.caption(f"{len(users)} tài khoản đã từng đăng nhập.")
    for u in sorted(users, key=lambda x: x["updated_at"], reverse=True):
        p = u.get("progress") or {}
        learned = len(p.get("learned_stts", []))
        quiz_log = p.get("quiz_log", [])
        correct = sum(1 for q in quiz_log if q.get("correct"))
        acc = round(100 * correct / len(quiz_log)) if quiz_log else 0
        xp = p.get("xp", 0)

        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1.4])
            with c1:
                status = "🚫 Đã khoá" if u["banned"] else "✅ Hoạt động"
                st.markdown(f"**{u['username']}** — {status}")
                st.caption(f"Hoạt động gần nhất: {u['updated_at'] or 'chưa rõ'}")
            c2.metric("Từ đã học", learned)
            c3.metric("Độ chính xác", f"{acc}%")
            c4.metric("XP", xp)
            with c5:
                if u["banned"]:
                    if st.button("Mở khoá", key=f"unban_{u['username']}", use_container_width=True):
                        store.set_banned(u["username"], False)
                        st.rerun()
                else:
                    if st.button("Khoá tài khoản", key=f"ban_{u['username']}", use_container_width=True, type="secondary"):
                        store.set_banned(u["username"], True)
                        st.rerun()


# =============================================================================
# ROUTER
# =============================================================================
STAGE_RENDERERS = {
    "home": render_home,
    "topic_picker": render_topic_picker,
    "batch_picker": render_batch_picker,
    "flashcard": render_flashcard,
    "quiz_entry": render_quiz_entry,
    "quiz_run": render_quiz_run,
    "phrase_learning": render_phrase_learning,
    "review_weak": render_review_weak,
    "dashboard": render_dashboard,
    "backup": render_backup,
    "admin_panel": render_admin_panel,
}

STAGE_RENDERERS.get(st.session_state.stage, render_home)()
