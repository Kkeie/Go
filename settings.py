import enum

from rgb import Rgb
from dataclasses import dataclass

BOARD_BROWN = Rgb(186, 138, 69)
BOARD_WIDTH = 1000
BOARD_BORDER = 120
STONE_RADIUS = 35
WHITE = Rgb(255, 255, 255)
BLACK = Rgb(0, 0, 0)
SCORE_POS = (BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER + 30)
DOT_RADIUS = 4
BUTTON_COLOR = Rgb(200, 200, 200)
BUTTON_HOVER_COLOR = Rgb(100, 100, 100)
BOARD_SIZES = [8, 9, 13, 19]
antialias_on = True
board_scale = {8: 1, 9: 0.9, 13: 0.7, 19: 0.5}


class GameModes(enum.StrEnum):
    PVP = "Игрок против игрока"
    EASY = "Лёгкий"
    DIFFICULTY = "Сложный"
