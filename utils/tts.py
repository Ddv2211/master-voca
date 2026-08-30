"""
Phát âm từ vựng bằng giọng đọc có sẵn của trình duyệt (Web Speech API —
`speechSynthesis`). Cách này KHÔNG cần gọi API ngoài, KHÔNG tốn phí, không
cần internet để tạo audio (chỉ cần trình duyệt hỗ trợ — Chrome/Edge/Safari
hiện đại đều hỗ trợ tốt).

Nếu sau này muốn giọng đọc tự nhiên hơn (ví dụ giọng Gemini TTS hoặc
gTTS), chỉ cần thay nội dung hàm `speak_button` mà không cần đổi chỗ gọi
ở app.py.
"""
from __future__ import annotations

import json

import streamlit as st


def speak_button(text: str, key: str, label: str = "🔊 Nghe phát âm",
                  autoplay: bool = False, rate: float = 0.9, height: int = 46):
    """
    Vẽ 1 nút bấm để phát âm `text` bằng tiếng Anh (giọng trình duyệt).
    `key` phải DUY NHẤT cho mỗi lần gọi (ví dụ f"speak_{stt}_{flipped}")
    để Streamlit tạo iframe mới mỗi khi từ/trạng thái thay đổi — điều
    này cũng giúp `autoplay=True` tự phát khi thẻ mới hiện ra.
    """
    safe_text = json.dumps(text)
    autoplay_js = "speak();" if autoplay else ""

    html = f"""
    <div style="display:flex; justify-content:center; align-items:center; height:100%;">
        <button id="btn-{key}" onclick="speak()" style="
            background:#eef2ff; color:#3730a3; border:1px solid #c7d2fe;
            border-radius:999px; padding:8px 18px; font-size:14px;
            font-weight:600; cursor:pointer; font-family:-apple-system,sans-serif;
        ">{label}</button>
    </div>
    <script>
        function speak() {{
            try {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance({safe_text});
                u.lang = "en-US";
                u.rate = {rate};
                window.speechSynthesis.speak(u);
            }} catch (e) {{ console.log("TTS not supported", e); }}
        }}
        {autoplay_js}
    </script>
    """
    st.iframe(html, height=height)
