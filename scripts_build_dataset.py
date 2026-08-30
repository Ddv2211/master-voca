"""
Tiền xử lý dữ liệu: gán CHỦ ĐỀ (topic) cho từng từ vựng bằng phương pháp
đối sánh từ khóa (heuristic keyword matching), sau đó xuất ra
data/vocabulary.json — file dữ liệu chính mà ứng dụng Streamlit sẽ dùng.

Chạy 1 lần khi build dữ liệu (không cần chạy lại khi deploy):
    python scripts_build_dataset.py

Ghi chú: cách gán chủ đề ở đây là heuristic (dựa theo từ khóa xuất hiện
trong nghĩa tiếng Việt). Nếu muốn chính xác hơn, có thể dùng Gemini để
phân loại lại toàn bộ danh sách (xem hàm `reclassify_with_gemini`
trong utils/gemini_client.py) rồi ghi đè trường "topic".
"""
import json
import re

SRC = "data/vocab_raw.json"
DST = "data/vocabulary.json"

# Mỗi chủ đề gồm: tên hiển thị + danh sách từ khóa (khớp trong "meaning" hoặc "word")
TOPICS = {
    "Văn phòng & Hành chính": [
        "văn phòng", "tài liệu", "hồ sơ", "ghi chú", "bìa", "ngăn kéo",
        "in", "fax", "hóa đơn", "biên bản", "báo cáo", "cuộc họp",
        "lịch làm việc", "công văn", "thư ký", "đơn xin", "bản ghi nhớ",
        "kẹp", "bút", "giấy",
    ],
    "Tài chính & Kế toán": [
        "tiền", "ngân hàng", "tài chính", "kế toán", "thuế", "lương",
        "chi phí", "ngân sách", "đầu tư", "cổ phần", "cổ phiếu", "nợ",
        "vay", "lãi", "thu nhập", "lợi nhuận", "hóa đơn", "kiểm toán",
        "chiết khấu", "giảm giá", "tiền tệ", "phá sản", "trả góp",
        "tín dụng", "bảo hiểm", "quỹ", "doanh thu", "vốn",
    ],
    "Nhân sự & Tuyển dụng": [
        "nhân viên", "ứng viên", "tuyển", "phỏng vấn", "sa thải",
        "nghỉ hưu", "lương", "chức vụ", "thăng chức", "nghỉ việc",
        "thực tập", "kinh nghiệm", "bằng cấp", "chứng chỉ", "đào tạo",
        "hợp đồng lao động", "nhân sự", "đơn xin việc", "hồ sơ xin việc",
    ],
    "Marketing & Bán hàng": [
        "quảng cáo", "tiếp thị", "khách hàng", "chiến dịch", "thương hiệu",
        "bán", "sản phẩm", "thị trường", "khuyến mãi", "doanh số",
        "người tiêu dùng", "cạnh tranh", "phiếu giảm giá",
    ],
    "Công nghệ": [
        "máy tính", "phần mềm", "trình duyệt", "tải xuống", "cài đặt",
        "kết nối", "thiết bị", "internet", "hệ thống", "trực tuyến",
        "công nghệ", "dữ liệu", "mạng", "kỹ thuật số", "nâng cấp",
    ],
    "Du lịch & Vận chuyển": [
        "chuyến bay", "hành khách", "hành lý", "sân bay", "khách sạn",
        "du lịch", "vé", "đặt phòng", "hành trình", "tàu", "xe",
        "du khách", "hộ chiếu", "hải quan", "giao thông", "vận chuyển",
        "tham quan", "tiếp viên",
    ],
    "Sản xuất & Kinh doanh": [
        "sản xuất", "nhà máy", "hàng hóa", "kho", "chuỗi", "cung cấp",
        "cửa hàng", "công ty", "doanh nghiệp", "xí nghiệp", "sáp nhập",
        "hợp nhất", "mua bán", "giao dịch", "đối tác", "cổ đông",
        "vận hành", "quy trình", "chất lượng", "kiểm tra",
    ],
    "Pháp lý & Hợp đồng": [
        "hợp đồng", "pháp lý", "luật", "quyền", "nghĩa vụ", "bằng sáng chế",
        "bản quyền", "cấm", "quy định", "trách nhiệm", "khiếu nại",
        "tranh chấp", "bồi thường", "phán xử", "thẩm phán",
    ],
    "Sức khỏe & An toàn": [
        "sức khỏe", "y học", "thuốc", "bệnh", "bác sĩ", "an toàn",
        "nguy hiểm", "khẩn cấp", "bảo hiểm y tế", "tiêm chủng", "chấn thương",
    ],
    "Giao tiếp & Cảm xúc": [
        "cảm thấy", "lo lắng", "vui", "buồn", "hài lòng", "thất vọng",
        "ngạc nhiên", "tự tin", "kiên nhẫn", "nhiệt tình", "bi quan",
        "lạc quan", "ghen", "sợ", "tin tưởng",
    ],
}

DEFAULT_TOPIC = "Từ vựng chung"


def guess_topic(word: str, meaning: str) -> str:
    text = f"{word} {meaning}".lower()
    best_topic, best_score = DEFAULT_TOPIC, 0
    for topic, keywords in TOPICS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_topic, best_score = topic, score
    return best_topic


def main():
    with open(SRC, encoding="utf-8") as f:
        rows = json.load(f)

    for r in rows:
        r["topic"] = guess_topic(r["word"], r["meaning"])
        # gom các từ thành từng nhóm học 10 từ/nhóm theo thứ tự gốc trong sách
        r["batch"] = (r["stt"] - 1) // 10 + 1

    topic_counts = {}
    for r in rows:
        topic_counts[r["topic"]] = topic_counts.get(r["topic"], 0) + 1

    print("Phân bố chủ đề:")
    for t, c in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"\nĐã ghi {len(rows)} từ vào {DST}")


if __name__ == "__main__":
    main()
