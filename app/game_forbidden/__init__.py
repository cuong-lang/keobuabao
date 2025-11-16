# app/game_forbidden/__init__.py
from flask import Blueprint

# Tên 'game_forbidden' này phải khớp với url_for
game_forbidden_bp = Blueprint('game_forbidden', __name__, template_folder='templates')

from . import routes