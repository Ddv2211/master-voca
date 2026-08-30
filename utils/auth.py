"""
Đăng nhập cho app — KHÔNG cho người dùng tự đăng ký. Toàn bộ tài khoản do
BẠN (admin) tạo sẵn trong Secrets của Streamlit Cloud (hoặc file
.streamlit/secrets.toml khi chạy local). Mật khẩu để dạng chữ thường
(plain text) trong secrets là AN TOÀN vì Secrets được Streamlit mã hoá
lưu trữ riêng, không nằm trong code/GitHub — thư viện `streamlit-
authenticator` sẽ tự băm (hash) mật khẩu mỗi khi app khởi động
(`auto_hash=True`), không lưu password dạng thô ở bất kỳ đâu khác.

Cấu trúc cần khai báo trong Secrets — xem `.streamlit/secrets.toml.example`.
"""
from __future__ import annotations

import streamlit as st
import streamlit_authenticator as stauth


def _to_plain_dict(obj):
    """st.secrets trả về kiểu AttrDict/Munch lồng nhau — chuyển hết sang
    dict/list Python thường để streamlit-authenticator xử lý được."""
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    if isinstance(obj, dict):
        return {k: _to_plain_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain_dict(v) for v in obj]
    return obj


def auth_configured() -> bool:
    try:
        return "credentials" in st.secrets and "usernames" in st.secrets["credentials"]
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _hashed_credentials(_fingerprint: str) -> dict:
    """
    Băm (hash) toàn bộ mật khẩu 1 lần và cache lại kết quả (đây là hàm
    thuần dữ liệu, KHÔNG tạo widget, nên cache an toàn) — để mỗi lần
    Streamlit rerun (xảy ra liên tục khi người dùng tương tác) không phải
    băm lại bcrypt cho từng tài khoản, tránh làm app bị chậm.
    """
    credentials = _to_plain_dict(st.secrets["credentials"])
    for username, info in credentials.get("usernames", {}).items():
        pw = info.get("password")
        if pw and not stauth.Hasher.is_hash(pw):
            info["password"] = stauth.Hasher.hash(pw)
    return credentials


def get_authenticator():
    """
    Lưu ý: Authenticate() tự tạo 1 widget quản lý cookie bên trong nó, nên
    KHÔNG được bọc st.cache_resource quanh chính lệnh gọi Authenticate() —
    phải khởi tạo lại mỗi lần rerun (đúng theo cách dùng chính thức của
    streamlit-authenticator). Chỉ phần băm mật khẩu ở trên mới nên cache.
    """
    fingerprint = str(sorted(st.secrets["credentials"]["usernames"].keys()))
    credentials = _hashed_credentials(fingerprint)
    cookie_cfg = _to_plain_dict(st.secrets.get("cookie", {}))
    return stauth.Authenticate(
        credentials=credentials,
        cookie_name=cookie_cfg.get("name", "toeic_app_auth"),
        cookie_key=cookie_cfg.get("key", "please_change_this_secret_key"),
        cookie_expiry_days=float(cookie_cfg.get("expiry_days", 30)),
        auto_hash=True,
    )


def login_gate():
    """
    Hiển thị form đăng nhập. Nếu đăng nhập thành công, trả về
    (authenticator, username, name, roles). Nếu chưa đăng nhập / sai mật
    khẩu / chưa cấu hình tài khoản, hiển thị thông báo phù hợp và
    `st.stop()` để không chạy phần còn lại của app.
    """
    if not auth_configured():
        st.error(
            "⚠️ App chưa được cấu hình tài khoản đăng nhập.\n\n"
            "Admin cần thêm mục `[credentials]` vào Settings → Secrets. "
            "Xem hướng dẫn trong README.md phần 'Đăng nhập & quản lý tài khoản'.",
            icon="🔒",
        )
        st.stop()

    authenticator = get_authenticator()
    authenticator.login(location="main", key="login_form")

    status = st.session_state.get("authentication_status")
    if status is False:
        st.error("❌ Sai tên đăng nhập hoặc mật khẩu.")
        st.stop()
    if status is None:
        st.info("👋 Vui lòng đăng nhập để bắt đầu học.")
        st.stop()

    username = st.session_state.get("username")
    name = st.session_state.get("name")
    roles = st.session_state.get("roles") or []
    return authenticator, username, name, roles


def is_admin(roles) -> bool:
    return bool(roles) and "admin" in roles
