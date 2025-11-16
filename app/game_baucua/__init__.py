from flask import Blueprint
game_baucua_bp = Blueprint('game_baucua', __name__, template_folder='templates')
from . import routes