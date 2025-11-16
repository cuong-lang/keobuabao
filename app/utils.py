# /app/utils.py
import random
import string

def create_deck():
    return ['Kéo', 'Búa', 'Bao'] * 2  # mỗi người 6 lá

def create_random_string(len: int) -> str:
    return ''.join(random.choices(string.ascii_uppercase, k=len))