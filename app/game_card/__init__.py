from flask import Blueprint
game_card_bp = Blueprint('game_card', __name__, template_folder='templates')
from . import routes