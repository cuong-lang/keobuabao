from flask import Blueprint
game_ai_bp = Blueprint('game_ai', __name__, template_folder='templates')
from . import routes