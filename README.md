# 🍜 VNFood Recognition

**Ứng dụng nhận diện món ăn Việt Nam từ hình ảnh bằng Google Gemini, xây dựng với Python và Streamlit.**

Tải ảnh món ăn lên, chọn vùng miền và ngôn ngữ, sau đó nhận kết quả gồm tên món ăn, mô tả, cách chế biến, cách thưởng thức và vùng được AI ước lượng là chứa món ăn chính.

> **Trạng thái:** Ứng dụng chạy cục bộ. Kết quả nhận diện, điểm tin cậy và vùng đánh dấu đều do AI ước lượng; không bảo đảm chính xác tuyệt đối.

## ✨ Tính năng

- 📸 **Nhận diện từ ảnh:** hỗ trợ JPG, JPEG và PNG.
- 🍽️ **Thông tin món ăn:** tên, vùng miền, mô tả, cách chế biến và cách thưởng thức.
- 🌐 **Hai ngôn ngữ:** Tiếng Việt và English.
- 🗺️ **Gợi ý vùng miền:** Bắc, Trung hoặc Nam (đây là thông tin gợi ý, không ép AI kết luận).
- 🎯 **Bounding box:** vẽ khung ước lượng quanh món ăn chính nếu Gemini trả về tọa độ hợp lệ.
- ⚡ **Cache cục bộ:** giảm số lần gọi API với cùng ảnh, vùng miền, ngôn ngữ và phiên bản model.
- 🔄 **Phân tích lại / Xóa cache:** làm mới kết quả khi cần.

## 🧰 Công nghệ

| Thành phần | Sử dụng |
| --- | --- |
| Ngôn ngữ | Python |
| Giao diện | Streamlit |
| Phân tích ảnh | Google Gemini API qua `google-genai` |
| Xử lý ảnh | Pillow |
| Lưu kết quả | JSON cache trên máy cục bộ |

Model được cấu hình tại `core/gemini_handler.py` (trong bản phát hành hiện tại: `gemini-3.5-flash-lite`). Khả dụng thực tế phụ thuộc vào Google Gemini API và tài khoản sử dụng.

## 🚀 Cài đặt và chạy trên Windows

**Yêu cầu:** Python và pip; một API Key Gemini hợp lệ. Có thể tạo API Key tại [Google AI Studio](https://aistudio.google.com/apikey).

**1. Tải dự án và mở PowerShell trong thư mục dự án**

Nếu đã đưa dự án lên GitHub, có thể clone bằng lệnh (thay URL bằng repository thật):

```powershell
git clone https://github.com/<your-username>/VNFood-Recognition.git
cd VNFood-Recognition
```

Nếu đã có mã nguồn trên máy, chỉ cần mở PowerShell trong thư mục `VNFood-Recognition`.

**2. Tạo môi trường ảo và cài thư viện**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**3. Cấu hình Gemini API Key**

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Mở `.streamlit/secrets.toml` và điền API Key của bạn:

```toml
[general]
GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"
```

> 🔐 **Bảo mật:** Không commit hoặc chia sẻ `secrets.toml`, API Key thật hay nội dung cache cá nhân. File mẫu `.streamlit/secrets.toml.example` không chứa khóa bí mật.

**4. Chạy ứng dụng**

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Mở URL localhost được Streamlit in trong terminal (thường là `http://localhost:8501`).

## 🖥️ Cách sử dụng

1. Ở thanh bên trái, chọn **Language** và **Region**.
2. Tải ảnh bằng ô **Upload a Vietnamese food image**.
3. Nhấn **Analyze / Phân tích**.
4. Xem ảnh đánh dấu món ăn (nếu có tọa độ), tên món, điểm tin cậy ước lượng và các phần mô tả.
5. Sử dụng **Reload Analysis** để gọi API lại, hoặc **Clear Cache** để xóa kết quả đã lưu.

## 📁 Cấu trúc thư mục

```text
VNFood-Recognition/
├── app.py                       # Giao diện Streamlit
├── core/
│   ├── gemini_handler.py        # Gọi Gemini và chuẩn hóa kết quả JSON
│   ├── image_tools.py           # Vẽ bounding box trên ảnh
│   └── utils.py                 # Cache key, đọc/ghi và xóa cache
├── tests/
│   └── test_core.py             # Unit tests
├── .streamlit/
│   └── secrets.toml.example     # Mẫu cấu hình (được phép commit)
├── requirements.txt
├── .gitignore
└── README.md
```

Các thư mục `.venv/`, `cache/` và file `.streamlit/secrets.toml` được tạo trên máy cục bộ và **không nên đưa lên GitHub**.

## ✅ Chạy kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kiểm thử cục bộ tập trung vào chuẩn hóa phản hồi AI, bounding box và khóa cache. Kiểm thử thực tế với Gemini cần API Key hợp lệ và hạn mức API còn khả dụng.

## 🧩 Dữ liệu đầu ra

Ứng dụng chuẩn hóa kết quả nhận diện thành một JSON object:

```json
{
  "food_name": "Phở bò",
  "confidence": 92,
  "region": "Miền Bắc",
  "description": "Mô tả món ăn...",
  "how_to_cook": "Các bước chế biến...",
  "how_to_eat": "Cách thưởng thức...",
  "bounding_box": {"x": 120, "y": 180, "width": 710, "height": 590}
}
```

*Đây chỉ là dữ liệu minh họa.* Tọa độ bounding box được chuẩn hóa trong khoảng **0–1000**, tính từ góc trên bên trái ảnh; `image_tools.py` quy đổi sang pixel khi vẽ. Nếu AI không xác định được khung, `bounding_box` có thể là `null`. Điểm `confidence` là mức tự đánh giá do mô hình tạo ra, **không phải xác suất đã hiệu chuẩn**.

## 🛠️ Xử lý sự cố thường gặp

| Triệu chứng | Cách kiểm tra |
| --- | --- |
| `StreamlitSecretNotFoundError` | Tạo `.streamlit/secrets.toml`, kiểm tra `[general]` và `GOOGLE_API_KEY`. |
| `404 NOT_FOUND` từ Gemini | Kiểm tra model trong `core/gemini_handler.py` và danh sách model tài khoản được phép truy cập. |
| API trả lỗi `403` hoặc `429` | Kiểm tra quyền truy cập API và quota trên Google AI Studio. |
| Không có bounding box | AI có thể trả `null` hoặc tọa độ không hợp lệ; ảnh gốc vẫn được hiển thị. |
| Kết quả không đổi | Nhấn **Reload Analysis** hoặc **Clear Cache**. |

## 🔒 Quyền riêng tư và lưu ý

Ảnh được gửi tới Gemini API để phân tích khi bạn yêu cầu nhận diện; hãy tránh tải lên ảnh có thông tin nhạy cảm nếu không có quyền chia sẻ. Kết quả cache được lưu cục bộ. Việc sử dụng Gemini API phải tuân thủ điều khoản và giới hạn dịch vụ của Google.

## 📌 Định hướng phát triển

- [ ] Bổ sung ảnh chụp màn hình/gif demo giao diện trong README.
- [ ] Mở rộng nhận diện nhiều món trong cùng một ảnh.
- [ ] Kiểm thử tích hợp API và cải thiện đánh giá chất lượng nhận diện.

---

**VNFood Recognition** — Exploring Vietnamese cuisine through computer vision and generative AI.
