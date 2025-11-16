import os
from pymongo import MongoClient

# === CẤU HÌNH KẾT NỐI MONGODB ===

# 1. ĐỌC CHUỖI KẾT NỐI TỪ BIẾN MÔI TRƯỜNG (Bắt buộc cho Hosting)
# Render/Railway sẽ cung cấp chuỗi kết nối công khai qua biến này
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    # 2. Fallback cho Phát triển Local (Nếu MONGO_URI không được thiết lập)
    print("WARNING: Biến môi trường MONGO_URI chưa được thiết lập. Đang dùng localhost.")
    # Sử dụng địa chỉ IP để tránh lỗi phân giải tên miền khi chạy local
    MONGO_URI = "mongodb://127.0.0.1:27017/LTM"

try:
    # 3. Kết nối
    client = MongoClient(MONGO_URI)

    # Lấy tên database từ URI hoặc mặc định
    # Nếu dùng Atlas, tên DB thường được chỉ định trong URI
    db = client.get_database("LTM")

    # Chỉ cần collection "users"
    users = db["users"]

    print("✅ Kết nối MongoDB thành công!")

except Exception as e:
    # Nếu kết nối thất bại (ví dụ: MongoDB chưa chạy trên local)
    print(f"❌ LỖI KẾT NỐI MONGODB: {e}")


    # Đặt giá trị mặc định để các hàm khác không bị crash
    class MockCollection:
        def find_one(self, *args, **kwargs): return {"username": "Guest", "currency": 1000}

        def update_one(self, *args, **kwargs): pass

        def find(self, *args, **kwargs): return []


    users = MockCollection()

# === KẾT THÚC CẤU HÌNH KẾT NỐI MONGODB ===