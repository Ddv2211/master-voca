# 📚 TOEIC 1000 — App học từ vựng thông minh (Streamlit + Gemini)

Ứng dụng học 1000 từ vựng TOEIC thông dụng nhất, gồm:

1. **Flashcard** học từ đơn (lật thẻ để xem nghĩa).
2. Sau khi học, tự động chuyển sang **bài điền từ vào ngữ cảnh** (câu ví dụ do
   Gemini tạo riêng cho từng từ, có fallback mẫu sẵn nếu chưa có API key).
3. Các bước **chuyển tiếp mượt mà, liên tục** (flashcard → điền từ → cụm từ →
   tổng kết) không cần rời trang.
4. **Tổng kết** tiến độ học tập + nhận xét cá nhân hoá từ Gemini, kèm danh
   sách từ hay sai để ôn lại.
5. Tích hợp **Gemini API** để: sinh câu ví dụ, sinh cụm từ liên quan, viết
   nhận xét học tập.
6. Sau khi thuộc từ đơn trong 1 nhóm, tiếp tục học **cụm từ (collocation)**
   thông dụng đi kèm từ đó.
7. Từ vựng được **gom theo chủ đề** (Văn phòng, Tài chính, Công nghệ, Du
   lịch...) để học theo nhu cầu, ngoài cách học tuần tự theo nhóm 10 từ.
8. **Đăng nhập bằng tài khoản do admin cấp** (không tự đăng ký) — tiến độ
   học được lưu riêng theo từng người và khôi phục khi đăng nhập lại;
   admin có trang quản trị để xem hoạt động và khoá/mở khoá từng tài khoản.
9. **Phát âm từ (Text-to-Speech)** ngay trên flashcard, có tuỳ chọn tự
   động đọc khi hiện thẻ mới.

Giao diện: thanh **tiến độ học tập cố định ở góc trên-trái** (nơi 90% người
dùng nhìn vào đầu tiên), menu **☰ 3 gạch** khi bấm sẽ xổ ngang các mục
chính, bấm vào 1 mục chính mới xổ tiếp các mục con bên dưới.

---

## 1. Cấu trúc thư mục

```
toeic-vocab-app/
├── app.py                       # App chính (điều hướng toàn bộ các màn hình)
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example     # Mẫu khai báo GEMINI_API_KEY
├── data/
│   ├── vocab_raw.json           # Dữ liệu thô trích từ PDF (STT/word/pos/phonetic/meaning)
│   └── vocabulary.json          # Dữ liệu đã gán topic + batch — APP DÙNG FILE NÀY
├── scripts_build_dataset.py     # Script build vocabulary.json (heuristic topic)
├── scripts_gemini_tag_topics.py # [Tuỳ chọn] Dùng Gemini phân loại topic chính xác hơn
└── utils/
    ├── data_loader.py           # Đọc & lọc dữ liệu từ vựng
    ├── gemini_client.py         # Gọi Gemini API (có fallback khi lỗi/thiếu key)
    ├── progress.py              # Theo dõi tiến độ học (session_state)
    └── ui.py                    # CSS + thanh tiến độ + menu điều hướng
```

## 2. Chạy thử ở máy local

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (tuỳ chọn) thêm Gemini API key để có câu ví dụ/cụm từ do AI tạo:
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# rồi mở file secrets.toml vừa tạo và dán API key thật vào

streamlit run app.py
```

Lấy API key Gemini miễn phí tại: https://aistudio.google.com/app/apikey

> Nếu **không** cấu hình `GEMINI_API_KEY`, app vẫn chạy bình thường — chỉ
> là câu ví dụ trong bài điền từ và cụm từ sẽ dùng mẫu có sẵn thay vì do
> AI sinh ra riêng cho từng từ.

## 3. Đưa lên GitHub

```bash
git init
git add .
git commit -m "TOEIC vocab learning app"
git branch -M main
git remote add origin https://github.com/<tên-bạn>/<tên-repo>.git
git push -u origin main
```

⚠️ File `.streamlit/secrets.toml` (chứa API key thật) đã được liệt kê trong
`.gitignore` — **không bao giờ commit file này lên GitHub công khai**.

## 4. Deploy lên Streamlit Community Cloud

1. Vào https://share.streamlit.io → **New app**.
2. Chọn repo GitHub vừa push, branch `main`, file chính là `app.py`.
3. Vào **Advanced settings → Secrets**, dán nội dung:
   ```toml
   GEMINI_API_KEY = "AIzaSy...key thật của bạn"
   GEMINI_MODEL = "gemini-2.5-flash"
   ```
4. Bấm **Deploy**. Sau 1-2 phút app sẽ có link dạng
   `https://<tên-app>.streamlit.app`.

## 5. Ghi chú quan trọng về dữ liệu & lưu tiến độ

- Streamlit Community Cloud là hosting **không có ổ đĩa vĩnh viễn**: mỗi khi
  app được deploy lại hoặc "ngủ" rồi thức dậy, mọi thứ ghi ra file trong lúc
  chạy sẽ bị mất. **Từ khi có tính năng đăng nhập (mục 8), vấn đề này đã
  được giải quyết bằng Google Sheets** — tiến độ mỗi tài khoản được đồng bộ
  lên đó ngay khi có thay đổi, và tải lại tự động mỗi lần đăng nhập.
- Nếu **chưa** cấu hình Google Sheets, tiến độ vẫn chỉ lưu trong
  `st.session_state` (mất khi đóng tab) — dùng tạm nút **"💾 Sao lưu tiến
  độ"** để tải file `.json` về máy rồi nhập lại ở buổi học sau.
- Muốn lưu tiến độ **vĩnh viễn, tự động, nhiều thiết bị** (bước nâng cấp
  tiếp theo), có thể thay `utils/progress.py` bằng một trong:
  - Google Sheets (qua `gspread` + service account) — miễn phí, dễ nhất.
  - Firebase Firestore (miễn phí, realtime).
  - Một database nhỏ như Supabase/PlanetScale (free tier).

## 6. Tên model Gemini

Tên model Gemini (ví dụ "gemini-2.5-flash") có thể thay đổi theo thời gian
khi Google phát hành phiên bản mới. Nếu app báo lỗi gọi API, hãy:
1. Vào https://ai.google.dev/gemini-api/docs/models để xem tên model hiện tại.
2. Cập nhật giá trị `GEMINI_MODEL` trong Secrets (không cần sửa code).

## 8. Đăng nhập & quản lý tài khoản (mới)

App yêu cầu đăng nhập trước khi học — **không có tự đăng ký**, chỉ bạn
(admin) mới tạo được tài khoản. Khi người dùng đăng nhập lại (kể cả ở
máy khác), tiến độ học được khôi phục tự động nếu đã bật lưu trữ Google
Sheets ở bước dưới.

### 8.1. Tạo tài khoản (bắt buộc)

Mở Secrets (local: `.streamlit/secrets.toml`, Cloud: Settings → Secrets)
và thêm:

```toml
[credentials]
[credentials.usernames.admin]
name = "Quản trị viên"
email = "admin@example.com"
password = "mat_khau_cua_ban"
roles = ["admin"]

[credentials.usernames.hocvien1]
name = "Học viên 1"
email = "hv1@example.com"
password = "123456"
roles = ["student"]

[cookie]
name = "toeic_app_auth"
key = "chuoi_bi_mat_ngau_nhien_cang_dai_cang_tot"
expiry_days = 30
```

- Mật khẩu để dạng chữ thường (plain text) là **an toàn** vì Secrets được
  Streamlit mã hoá lưu riêng, tách biệt khỏi code/GitHub — app tự băm
  (bcrypt) mật khẩu mỗi lần chạy, không lưu dạng thô ở đâu khác.
- `roles = ["admin"]` → tài khoản này thấy thêm menu **"🛠️ Quản trị"**.
- Muốn thêm/xoá/đổi mật khẩu tài khoản nào: sửa trực tiếp trong Secrets
  rồi lưu lại — không cần sửa code, không cần redeploy.

### 8.2. Lưu tiến độ vĩnh viễn qua Google Sheets (khuyến nghị)

Không bắt buộc — nếu bỏ qua, app vẫn chạy nhưng tiến độ mỗi tài khoản
chỉ tồn tại trong phiên đăng nhập hiện tại (mất khi app khởi động lại).

**Bước 1 — Tạo Google Sheet:**
1. Vào https://sheets.google.com → tạo 1 spreadsheet mới, đặt tên tuỳ ý
   (ví dụ "TOEIC App Data").
2. Copy **Spreadsheet ID** từ URL, ví dụ với URL
   `https://docs.google.com/spreadsheets/d/1AbCxyz.../edit`
   thì ID là `1AbCxyz...`.

**Bước 2 — Tạo Service Account (tài khoản máy để app dùng ghi vào Sheet):**
1. Vào https://console.cloud.google.com/ → tạo project mới (hoặc dùng
   project có sẵn).
2. Vào **APIs & Services → Library**, bật **Google Sheets API** và
   **Google Drive API**.
3. Vào **APIs & Services → Credentials → Create Credentials → Service
   account**, đặt tên tuỳ ý, bấm **Create and Continue → Done**.
4. Mở service account vừa tạo → tab **Keys → Add key → Create new key
   → JSON** → tải file `.json` về máy.

**Bước 3 — Chia sẻ Sheet cho service account:**
1. Mở file `.json` vừa tải, tìm giá trị `client_email` (dạng
   `xxx@xxx.iam.gserviceaccount.com`).
2. Vào Google Sheet đã tạo ở Bước 1 → **Share** → dán email đó vào →
   chọn quyền **Editor** → Send.

**Bước 4 — Dán thông tin vào Secrets:**

```toml
[sheets]
spreadsheet_id = "1AbCxyz...ID_bạn_copy_ở_bước_1"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "xxx@xxx.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Copy nguyên văn từng giá trị từ file `.json` đã tải sang các dòng tương
ứng ở trên (giữ nguyên `\n` bên trong `private_key`). Lưu Secrets, app sẽ
tự động dùng Google Sheets từ lần chạy tiếp theo — không cần sửa code.

### 8.3. Trang Quản trị (dành cho tài khoản có `roles = ["admin"]`)

Vào menu ☰ → **🛠️ Quản trị → Quản lý tài khoản** để xem:
- Danh sách mọi tài khoản đã từng đăng nhập.
- Thời gian hoạt động gần nhất, số từ đã học, độ chính xác, điểm XP —
  giúp bạn **nhận biết hoạt động** của từng người học.
- Nút **"Khoá tài khoản" / "Mở khoá"** — dùng để **trục xuất** (chặn
  đăng nhập) một tài khoản ngay lập tức mà không cần xoá khỏi Secrets;
  tài khoản bị khoá vẫn tồn tại nhưng sẽ thấy thông báo "đã bị khoá" và
  bị đăng xuất khi thử vào app.

> Muốn xoá hẳn 1 tài khoản (không cho đăng nhập lại dù không bị khoá):
> xoá khối `[credentials.usernames.<tên>]` tương ứng khỏi Secrets.

## 9. Cải thiện chủ đề (topic) từ vựng chính xác hơn

`scripts_build_dataset.py` gán chủ đề bằng cách dò từ khóa trong nghĩa
tiếng Việt (heuristic) — khá nhiều từ sẽ rơi vào nhóm "Từ vựng chung" vì
nghĩa quá ngắn để dò từ khóa chính xác. Nếu muốn phân loại chính xác hơn
bằng AI, chạy (1 lần, không ảnh hưởng lúc deploy):

```bash
export GEMINI_API_KEY="AIza..."
pip install google-generativeai
python scripts_gemini_tag_topics.py
```

Script sẽ ghi đè trường `"topic"` trong `data/vocabulary.json` — nhớ
`git add/commit/push` lại file này sau khi chạy xong.
