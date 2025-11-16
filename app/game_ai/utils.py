# /app/game_ai/utils.py
from flask import session
import random

def update_user_history(user_choice):
    if 'sp_history' not in session:
        session['sp_history'] = []
    session['sp_history'].append(user_choice)
    if len(session['sp_history']) > 100:
        session['sp_history'].pop(0)
    session.modified = True

def predict_user_move():
    if 'sp_history' not in session or len(session['sp_history']) < 2:
        return random.choice(['rock', 'paper', 'scissor'])
    last_move = session['sp_history'][-1]
    transitions = {}
    history_to_analyze = session['sp_history'][:-1]
    for i in range(len(history_to_analyze) - 1):
        current, next_m = history_to_analyze[i], history_to_analyze[i + 1]
        if current not in transitions:
            transitions[current] = {}
        if next_m not in transitions[current]:
            transitions[current][next_m] = 0
        transitions[current][next_m] += 1
    if last_move not in transitions or not transitions[last_move]:
        return random.choice(['rock', 'paper', 'scissor'])
    possible_next_moves = transitions[last_move]
    predicted_move = max(possible_next_moves, key=possible_next_moves.get)
    return predicted_move

def get_bot_choice_random():
    return random.choice(['rock', 'paper', 'scissor'])

def get_winning_move(move):
    if move == 'rock': return 'paper'
    if move == 'paper': return 'scissor'
    if move == 'scissor': return 'rock'
    return random.choice(['rock', 'paper', 'scissor'])

def determine_winner(player_choice, ai_choice):
    if player_choice == ai_choice:
        return 'TIE'
    if (player_choice == 'rock' and ai_choice == 'scissor') or \
            (player_choice == 'paper' and ai_choice == 'rock') or \
            (player_choice == 'scissor' and ai_choice == 'paper'):
        return 'player_win'
    return 'ai_win'