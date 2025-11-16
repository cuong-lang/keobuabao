# /app/__init__.py
from flask import Flask
from .config import Config
from .extensions import socketio

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Khởi tạo extensions với app
    socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')

    # Đăng ký các Blueprints (các file routes)
    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from .main.routes import main_bp
    app.register_blueprint(main_bp)

    from .game_ai.routes import game_ai_bp
    # Thêm prefix để đường dẫn thành: /game_ai/...
    app.register_blueprint(game_ai_bp, url_prefix='/game_ai')

    from .game_baucua.routes import game_baucua_bp
    # QUAN TRỌNG: Thêm prefix để đường dẫn thành: /game_baucua/
    app.register_blueprint(game_baucua_bp, url_prefix='/game_baucua')

    from .game_card.routes import game_card_bp
    app.register_blueprint(game_card_bp, url_prefix='/game_card')

    # --- SỬA LỖI: THÊM 2 DÒNG NÀY ---
    from .game_forbidden.routes import game_forbidden_bp
    app.register_blueprint(game_forbidden_bp, url_prefix='/game_forbidden')
    # --- KẾT THÚC SỬA ---

    # Import file events.py để đăng ký các hàm @socketio.on
    # Phải import ở cuối để tránh circular imports
    from . import events

    return app