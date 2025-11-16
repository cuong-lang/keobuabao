# app/main/routes.py
from flask import render_template, url_for, session, redirect, jsonify, request, flash
import html
from . import main_bp
from ..models import User
from ..database import users
from ..forms import JoinRoom, editUserForm


@main_bp.route("/lobby/", methods=["GET"])
def lobby_page():
    if "username" in session:
        if 'sp_history' in session:
            session.pop('sp_history')
        join_room_form = JoinRoom()
        return render_template('lobby.html',
                               form=join_room_form,
                               username=html.escape(session["username"]),
                               currency=session.get("currency", 1000))
    else:
        return redirect(url_for("auth.login_page"))


@main_bp.route('/game/<string:room_id>')
def game_page(room_id):
    if "username" not in session:
        flash("Bạn cần đăng nhập để vào phòng!", "error")
        return redirect(url_for("auth.login_page"))
    return render_template('game.html',
                           username=html.escape(session["username"]),
                           currency=session.get("currency", 1000))


@main_bp.route("/about/")
def about_page():
    return render_template('about.html')


@main_bp.route("/profile/")
def profileCheck():
    if session.get("username") == None:
        return jsonify({"failed": "Login first to view profiles."}), 401
    return redirect(url_for('main.profile_page', username=session.get("username")))


@main_bp.route('/profile/<string:username>', methods=['GET'])
def profile_page(username):
    user = users.find_one({"username": username})
    user_board = users.find({}).sort("wins", -1)
    sorted_user_board = [user for user in user_board]
    user_rank = -1
    if user in sorted_user_board:
        user_rank = sorted_user_board.index(user) + 1
    if user and 'username' in session:
        editUsernameForm = editUserForm()
        return render_template('profile.html', form=editUsernameForm, user=user,
                               username=html.escape(session.get('username')), rank=user_rank,
                               currency=session.get("currency", 1000))
    elif user and 'username' not in session:
        editUsernameForm = editUserForm()
        return render_template('profile.html', form=editUsernameForm, user=user, username="", rank=user_rank,
                               currency=0)
    else:
        flash("User can not be found", "error")
        return redirect(url_for('main.lobby_page'))


@main_bp.route('/profile/<string:username>', methods=['POST'])
def edit_username(username):
    if session.get("username") != username:
        return jsonify({"failed": "In order to change this account's username, please login."}), 401
    form = editUserForm()
    if form.validate_on_submit():
        newUsername = form.newUsername.data
        is_avialable_name = users.find_one({"username": newUsername}) == None
        is_valid_name = '/' not in newUsername
        if not is_avialable_name:
            flash("Username already in use", "error")
            return redirect(url_for('main.profile_page', username=session.get("username")))
        if not is_valid_name:
            flash("Username cannot contain '/' !", "error")
            return redirect(url_for('main.profile_page', username=session.get("username")))

        users.find_one_and_update({"username": session.get("username")}, {"$set": {'username': newUsername}})
        session["username"] = newUsername
        flash("Username changed successfully!", "success")
        return redirect(url_for('main.profile_page', username=newUsername))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'error')
        return redirect(url_for('main.profile_page', username=session.get("username")))


#
# === SỬA HÀM NÀY ĐỂ LEADERBOARD CHẠY ===
#
@main_bp.route('/leaderboard/')
def leaderboard_page():
    # Lấy tất cả các trường cần thiết
    projection = {
        "username": 1,
        "wins": 1,             # Thắng PvP Kéo Búa Bao
        "played": 1,           # Số trận PvP
        "baucua_winnings": 1,  # Tiền thắng Bầu Cua
        "forbidden_wins": 1,   # Số lần thắng Tử Cấm
        "_id": 0
    }

    # 1. Bảng XH PvP (Kéo Búa Bao) - Sắp xếp theo "wins"
    user_board_cursor = users.find(
        {"played": {"$gt": 0}}, # Chỉ lấy người đã chơi
        projection
    ).sort("wins", -1).limit(100)
    user_board = list(user_board_cursor)

    # 2. THÊM: Bảng XH Bầu Cua (Top "đại gia") - Sắp xếp theo "baucua_winnings"
    baucua_board_cursor = users.find(
        {"baucua_winnings": {"$gt": 0}}, # Chỉ lấy người có thắng
        projection
    ).sort("baucua_winnings", -1).limit(100)
    baucua_board = list(baucua_board_cursor)

    # 3. THÊM: Bảng XH Tử Cấm (Top "thần bài") - Sắp xếp theo "forbidden_wins"
    forbidden_board_cursor = users.find(
        {"forbidden_wins": {"$gt": 0}}, # Chỉ lấy người có thắng
        projection
    ).sort("forbidden_wins", -1).limit(100)
    forbidden_board = list(forbidden_board_cursor)

    # Truyền cả 3 bảng xếp hạng sang template
    return render_template('leaderboard.html',
                           boards=user_board,             # Board PvP
                           baucua_boards=baucua_board,      # Board Bầu Cua
                           forbidden_boards=forbidden_board, # Board Tử Cấm
                           title="Leaderboard",
                           currency=session.get("currency", 1000))