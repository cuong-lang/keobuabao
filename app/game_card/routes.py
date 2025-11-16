from flask import render_template
from . import game_card_bp

@game_card_bp.route('/cardgame')
def index_card_game():
    return render_template('index.html')