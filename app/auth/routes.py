# app/auth/routes.py
from flask import render_template, url_for, session, redirect, request
from . import auth_bp
from ..models import User  # Sửa: ..models
from ..forms import LoginForm, RegistrationForm # Sửa: ..forms

@auth_bp.route('/', methods=["POST", "GET"])
def login_page():
    if "username" in session:
        return redirect(url_for("main.lobby_page")) # Dòng này đã đúng
    login_form = LoginForm()
    if login_form.validate_on_submit():
        return User().login(login_form)
    return render_template('login.html', form=login_form)

@auth_bp.route('/signup/', methods=["POST", "GET"])
def signup_page():
    registration_form = RegistrationForm()
    if registration_form.validate_on_submit():
        return User().signup()
    return render_template('register.html', form=registration_form)

@auth_bp.route("/profile/signout")
def signout_page():
    return User().signout()