# app/models.py
from flask import Flask, jsonify, request, session, redirect, url_for, flash
from .database import users
import uuid
import datetime
from .forms import LoginForm
import bcrypt  # BẠN BỊ THIẾU IMPORT NÀY TRONG FILE GỐC


class User:

    def start_session(self, user):
        session['logged_in'] = True
        session['userid'] = user["_id"]
        session["username"] = user["username"]
        session["currency"] = user.get("currency", 1000)
        session.modified = True  # Đảm bảo session được lưu

        # SỬA: Luôn chuyển hướng đến lobby_page
        return redirect(url_for('main.lobby_page'))

    def signup(self):
        salt = bcrypt.gensalt()

        is_valid_username = '/' not in request.form.get('username')
        if not is_valid_username:
            flash("Usernames cannot contain '/' !", "error")
            return redirect(url_for('auth.signup_page'))  # Sửa: Dùng url_for

        user = {
            "_id": uuid.uuid4().hex,
            "username": request.form.get('username'),
            "email": request.form.get('email'),
            "salt": salt,
            "password": bcrypt.hashpw(request.form.get('password').encode(), salt),

            # --- Stats Cũ ---
            "wins": 0,
            "played": 0,
            "currency": 1000,
            "last_login": datetime.datetime.utcnow(),

            # --- THÊM STATS MỚI CHO LEADERBOARD ---
            "baucua_winnings": 0,  # Tổng tiền thắng/thua ròng
            "forbidden_wins": 0  # Số lần thắng (cash out) ở Chế độ Tử Cấm
        }

        if users.find_one({"email": user['email']}):
            flash("Email address already in use", "error")
            return redirect(url_for('auth.signup_page'))  # Sửa: Dùng url_for

        if users.find_one({"username": user['username']}):
            flash("Username already in use", "error")
            return redirect(url_for('auth.signup_page'))  # Sửa: Dùng url_for

        users.insert_one(user)
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('auth.login_page'))  # Sửa: Dùng url_for

    def signout(self):
        session.clear()
        flash("Successfully signed out!", "success")
        return redirect(url_for('auth.login_page'))  # Sửa: Dùng url_for

    def login(self, form: LoginForm):
        remember_me = form.remember.data
        userFound: dict = users.find_one({"email": request.form.get('email')})

        if userFound and bcrypt.hashpw(request.form.get('password').encode(), userFound['salt']) == userFound[
            'password']:

            last_login = userFound.get('last_login', datetime.datetime.min)
            today = datetime.datetime.utcnow()

            if last_login.date() < today.date():
                users.update_one(
                    {"_id": userFound["_id"]},
                    {
                        "$inc": {"currency": 100},
                        "$set": {"last_login": today}
                    }
                )
                userFound["currency"] = userFound.get("currency", 1000) + 100
                flash("Bạn nhận được 100v cho lần đăng nhập hôm nay!", "success")
            else:
                if "currency" not in userFound:
                    users.update_one(
                        {"_id": userFound["_id"]},
                        {"$set": {"currency": 1000}}
                    )
                    userFound["currency"] = 1000

            if remember_me:
                session.permanent = True
            else:
                session.permanent = False

            return self.start_session(userFound)

        flash("Wrong password or invalid email.", "error")
        return redirect(url_for('auth.login_page'))  # Sửa: Dùng url_for