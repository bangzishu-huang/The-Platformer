import pygame
from os import walk
from os.path import join
from pytmx.util_pygame import load_pygame

WINDOW_WIDTH, WINDOW_HEIGHT = 1440, 800
TILE_SIZE = 64
FRAMERATE = 60
BG_COLOR = "#ffd9c0"

HIGHSCORE_FILE = join('code', 'data', 'highscore.txt')
DIFFICULTIES = {
    'easy': {'label': 'EASY', 'color': '#a8d5a2', 'bee_interval': 900, 'bee_speed': (200, 300), 'worm_speed_mult': 0.8, 'worm_interval': 4000},
    'medium': {'label': 'MEDIUM', 'color': '#f5c98c', 'bee_interval': 600, 'bee_speed': (300, 450), 'worm_speed_mult': 1.0, 'worm_interval': 3000},
    'hard': {'label': 'HARD', 'color': '#e59a9a', 'bee_interval': 350, 'bee_speed': (600, 800), 'worm_speed_mult': 1.6, 'worm_interval': 3000},
    'impossible': {'label': 'IMPOSSIBLE', 'color': '#6b6b6b', 'bee_interval': 180, 'bee_speed': (600, 800), 'worm_speed_mult': 1.6, 'worm_interval': 1200},
}

POWERUPS = {
    'rapid_fire': {'label': 'RAPID FIRE', 'color': '#f5c98c'},
    'speed_boost': {'label': 'SPEED BOOST', 'color': '#a8d5a2'},
    'shield': {'label': 'SHIELD', 'color': '#9ec9e2'},
    'piercing': {'label': 'PIERCING_SHOT', 'color': '#c9a8d5'},
    'multi_shot': {'label': 'MULTI SHOT', 'color': '#a8c9d5'},
    'score_x2': {'label': 'DOUBLE SCORE', 'color': '#f5e28c'}
}
POWERUP_DURATION = 20000
LOTTERY_SPIN_TIME = 1500
KILLS_PER_LOTTERY = 10