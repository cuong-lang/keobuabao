import eventlet
import os

eventlet.monkey_patch()  # Rất quan trọng cho async_mode='eventlet'

from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    # Lấy PORT từ biến môi trường của hệ thống hosting (Render/Railway)
    port = int(os.environ.get("PORT", 8080))

    print(f"Server (SocketIO Eventlet) đang khởi động tại {os.environ.get('HOST', '0.0.0.0')}:{port}")

    # === CẤU HÌNH BẮT BUỘC CHO HOSTING CÔNG CỘNG ===
    # host='0.0.0.0' để lắng nghe tất cả các giao diện mạng
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,  # Tắt debug khi deploy
        allow_unsafe_werkzeug=True,
        use_reloader=False  # Bắt buộc tắt reloader khi dùng eventlet
    )