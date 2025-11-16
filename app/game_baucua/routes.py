# app/game_baucua/routes.py
from flask import render_template, session, redirect, url_for, flash
import html
from . import game_baucua_bp


@game_baucua_bp.route("/")
@game_baucua_bp.route("/<string:room_id>")
def baucua_entry(room_id=None):
    if "username" not in session:
        flash("Bạn cần đăng nhập!", "error")
        return redirect(url_for("auth.login_page"))

    # --- THÊM DÒNG NÀY ---
    # Import danh sách phòng từ events.py
    from ..events import baucua_rooms
    # ---------------------

    return render_template('game_baucua_6.html',
                           username=html.escape(session["username"]),
                           room_id=room_id,
                           rooms=baucua_rooms,  # <-- TRUYỀN BIẾN NÀY SANG HTML
                           currency=session.get("currency", 1000))