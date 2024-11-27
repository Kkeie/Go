from settings import *
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    x: int
    y: int

    def point_to_colrow(self, size: int) -> tuple[int, int]:
        """
        Преобразует пиксельные координаты в индексы столбца и строки.

        Args:
            size (int): Размер доски.

        Returns:
            tuple[int, int]: Индексы (col, row) на доске.
        """
        inc = (BOARD_WIDTH - 2 * BOARD_BORDER) / (size - 1)
        x_dist = self.x - BOARD_BORDER
        y_dist = self.y - BOARD_BORDER
        col = round(x_dist / inc)
        row = round(y_dist / inc)
        return col, row

    @classmethod
    def colrow_to_point(cls, col: int, row: int, size: int) -> 'Point':
        """
        Преобразует индексы столбца и строки в пиксельные координаты.

        Args:
            col (int): Индекс столбца.
            row (int): Индекс строки.
            size (int): Размер доски.

        Returns:
            Point: Объект Point с координатами x и y.
        """
        inc = (BOARD_WIDTH - 2 * BOARD_BORDER) / (size - 1)
        x = int(BOARD_BORDER + col * inc)
        y = int(BOARD_BORDER + row * inc)
        return cls(x=x, y=y)
