# /app/config.py
import os
from datetime import timedelta

class Config:
    # Áp dụng fix bảo mật: Lấy key từ biến môi trường
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', b'cse312 group project secret key')
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)