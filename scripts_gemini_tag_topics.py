"""
[TÙY CHỌN — nâng cao] Dùng Gemini để phân loại 1000 từ vào các chủ đề
chính xác hơn heuristic từ khóa trong scripts_build_dataset.py.

Cách dùng:
    1. pip install google-generativeai
    2. export GEMINI_API_KEY="AIza..."
    3. python scripts_gemini_tag_topics.py

Kết quả: ghi đè trường "topic" trong data/vocabulary.json.
Script gọi Gemini theo từng lô (batch) 40 từ/lần để tiết kiệm token,
yêu cầu Gemini trả về JSON thuần {stt: topic}.

Lưu ý: đây là bước tiền xử lý dữ liệu (chạy 1 lần, offline).
Ứng dụng Streamlit khi deploy KHÔNG cần chạy script này — nó chỉ đọc
data/vocabulary.json đã có sẵn trường "topic".
"""
import json
import os
import time

import google.generativeai as genai

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DATA_PATH = "data/vocabulary.json"
BATCH_SIZE = 40

TOPIC_LIST = [
    "Văn phòng & Hành chính", "Tài chính & Kế toán", "Nhân sự & Tuyển dụng",
    "Marketing & Bán hàng", "Công nghệ", "Du lịch & Vận chuyển",
    "Sản xuất & Kinh doanh", "Pháp lý & Hợp đồng", "Sức khỏe & An toàn",
    "Giao tiếp & Cảm xúc", "Từ vựng chung",
]

PROMPT_TMPL = """Bạn là chuyên gia từ vựng TOEIC. Dưới đây là danh sách từ
tiếng Anh kèm nghĩa tiếng Việt. Hãy phân mỗi từ vào ĐÚNG MỘT chủ đề
trong danh sách sau (chỉ chọn trong danh sách, không tạo chủ đề mới):
{topics}

Danh sách từ (định dạng "stt. word - nghĩa"):
{words}

Chỉ trả về JSON hợp lệ, KHÔNG kèm giải thích, KHÔNG dùng markdown fences,
theo định dạng: {{"stt_so": "ten_chu_de", ...}}
"""


def classify_batch(model, batch):
    words_text = "\n".join(f"{r['stt']}. {r['word']} - {r['meaning']}" for r in batch)
    prompt = PROMPT_TMPL.format(topics=", ".join(TOPIC_LIST), words=words_text)
    resp = model.generate_content(prompt)
    text = resp.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Chưa đặt biến môi trường GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    with open(DATA_PATH, encoding="utf-8") as f:
        rows = json.load(f)

    by_stt = {r["stt"]: r for r in rows}
    stts = sorted(by_stt)

    for i in range(0, len(stts), BATCH_SIZE):
        batch_ids = stts[i:i + BATCH_SIZE]
        batch = [by_stt[s] for s in batch_ids]
        try:
            mapping = classify_batch(model, batch)
        except Exception as e:
            print(f"  Lỗi ở batch {i}-{i+BATCH_SIZE}: {e}. Bỏ qua, giữ topic cũ.")
            continue
        for stt_str, topic in mapping.items():
            stt = int(stt_str)
            if topic in TOPIC_LIST and stt in by_stt:
                by_stt[stt]["topic"] = topic
        print(f"Đã phân loại {min(i + BATCH_SIZE, len(stts))}/{len(stts)} từ")
        time.sleep(1.2)  # tránh vượt rate limit

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print("Hoàn tất — đã cập nhật data/vocabulary.json")


if __name__ == "__main__":
    main()
