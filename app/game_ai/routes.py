from flask import render_template, url_for, session, redirect, jsonify, request
from . import game_ai_bp
from ..database import users  # Sửa
from .utils import *  # Import logic AI từ file utils riêng


@game_ai_bp.route('/single/', methods=['GET'])
def single_player_page():
    if "username" in session:
        if 'sp_history' in session:
            session.pop('sp_history')
        return render_template('single.html',
                               username=session["username"],
                               currency=session.get("currency", 1000))
    else:
        return redirect(url_for("auth.login_page"))  # Sửa


@game_ai_bp.route('/ai_move', methods=['POST'])
def ai_move():
    try:
        data = request.get_json()
        player_choice = data['player_choice']
        if player_choice not in ['rock', 'paper', 'scissor']:
            return jsonify({'error': 'Lựa chọn không hợp lệ'}), 400

        # Gọi hàm logic từ utils
        last_prediction = predict_user_move()
        update_user_history(player_choice)
        next_habit_prediction = predict_user_move()
        next_suggestion = get_winning_move(next_habit_prediction)
        ai_opponent_choice = get_bot_choice_random()
        result = determine_winner(player_choice, ai_opponent_choice)

        if result == 'player_win' and 'username' in session:
            users.update_one(
                {"username": session['username']},
                {"$inc": {"currency": 10}}
            )
            session['currency'] = session.get('currency', 1000) + 10
            session.modified = True

        return jsonify({
            'ai_choice': ai_opponent_choice,
            'result': result,
            'last_prediction': last_prediction,
            'prediction_correct': (player_choice == last_prediction),
            'next_suggestion': next_suggestion,
            'new_currency': session.get('currency')
        })
    except Exception as e:
        print(f"Lỗi trong /ai_move: {e}")
        return jsonify({'error': str(e)}), 500