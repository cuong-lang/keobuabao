# app/game_forbidden/routes.py
from flask import render_template, session, redirect, url_for, flash
import html
from . import game_forbidden_bp  # Import Blueprint

# Import danh sách phòng từ events.py
from ..events import forbidden_rooms


#
# === SỬA LỖI 404 TẠI ĐÂY ===
#
# Route 1: Dành cho Sảnh ( /game_forbidden/ )
@game_forbidden_bp.route("/")
# Route 2: Dành cho vào phòng ( /game_forbidden/<room_id> )
@game_forbidden_bp.route("/<string:room_id>")
def forbidden_entry(room_id=None):
    if "username" not in session:
        flash("Bạn cần đăng nhập!", "error")
        return redirect(url_for("auth.login_page"))

    # Render file HTML "2 trong 1"
    return render_template('game_forbidden.html',
                           username=html.escape(session["username"]),
                           room_id=room_id,
                           rooms=forbidden_rooms,  # Gửi danh sách phòng
                           currency=session.get("currency", 1000))
#
# === KẾT THÚC SỬA ===
#