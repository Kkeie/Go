from typing import Tuple
import numpy as np

from Settings import *


class Point:
    def __init__(self):
        self.x, self.y = 0, 0

    def set_x(self, x: int) -> None:
        self.x = x

    def set_y(self, y: int) -> None:
        self.y = y

    def point_to_colrow(self, size: int) -> Tuple[int, int]:
        inc = (BOARD_WIDTH - 2 * BOARD_BORDER) / (size - 1)
        x_dist = self.x - BOARD_BORDER
        y_dist = self.y - BOARD_BORDER
        col = round(x_dist / inc)
        row = round(y_dist / inc)
        return col, row

    def colrow_to_point(self, col: int, row: int, size: int):
        point = Point()
        inc = (BOARD_WIDTH - 2 * BOARD_BORDER) / (size - 1)
        x = int(BOARD_BORDER + col * inc)
        y = int(BOARD_BORDER + row * inc)
        point.set_x(x)
        point.set_y(y)
        return point

