import itertools

import networkx as nx
import numpy as np

from point import Point
from settings import *


class Game_logic:
    def __init__(self, size: int) -> None:
        self.size = size
    def get_grid_points(self, size: int) -> tuple[list[Point], list[Point]]:
        end_points: list[Point] = []
        start_points: list[Point] = []
        start_coords, end_coords = [], []
        xs = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
        ys = np.full(size, BOARD_BORDER)
        start_coords.extend(zip(xs, ys))
        xs = np.full(size, BOARD_BORDER)
        ys = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
        start_coords.extend(zip(xs, ys))
        xs = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
        ys = np.full(size, BOARD_WIDTH - BOARD_BORDER)
        end_coords.extend(zip(xs, ys))
        xs = np.full(size, BOARD_WIDTH - BOARD_BORDER)
        ys = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
        end_coords.extend(list(zip(xs, ys)))
        for x, y in end_coords:
            end_points.append(Point(x, y))
        for x, y in start_coords:
            start_points.append(Point(x, y))
        return start_points, end_points

    def stone_group_has_no_liberties(self, board: np.ndarray, group: set[Point]) -> bool:
        for point in group:
            if point.x > 0 and board[point.x - 1, point.y] == 0:
                return False
            if point.y > 0 and board[point.x, point.y - 1] == 0:
                return False
            if point.x < board.shape[0] - 1 and board[point.x + 1, point.y] == 0:
                return False
            if point.y < board.shape[0] - 1 and board[point.x, point.y + 1] == 0:
                return False
        return True

    from typing import Iterable
    from point import Point  # Импортируем ваш класс Point

    def get_stone_groups(self, board: np.ndarray, color: str) -> Iterable[set[Point]]:
        """
        Возвращает группы камней указанного цвета на доске.

        Args:
            board (np.ndarray): Игровая доска (2D массив).
            color (str): Цвет камней ("white" или "black").

        Returns:
            Iterable[Set[Point]]: Итератор с наборами точек, представляющими группы камней.
        """
        size = board.shape[0]
        color_code = 1 if color == "white" else 2
        xs, ys = np.where(board == color_code)  # Получаем координаты камней
        graph = nx.grid_graph(dim=[size, size])
        stones = set(zip(xs, ys))  # Преобразуем координаты в набор
        all_spaces = set(itertools.product(range(size), range(size)))
        stones_to_remove = all_spaces - stones
        graph.remove_nodes_from(stones_to_remove)  # Удаляем узлы, не принадлежащие камням
        return list(set(Point(x, y) for x, y in group) for group in nx.connected_components(graph))

    def get_group(self, board: np.ndarray, position: Point) -> set[Point]:

        color = board[position.x, position.y]
        if color == 0:
            return set()

        group = set()
        stack = [position]

        while stack:
            current = stack.pop()
            if current in group:
                continue
            group.add(current)
            for neighbor in self.get_adjacent_positions({current}, self.size):
                if board[neighbor.x, neighbor.y] == color and neighbor not in group:
                    stack.append(neighbor)

        result_points = set()
        for coord in group:
            result_points.add(Point(coord.x, coord.y))

        return result_points

    def count_liberties(self, board: np.ndarray, group: set[Point]) -> int:
        liberties = set()
        for point in group:
            for neighbor in self.get_adjacent_positions(group, self.size):
                if board[neighbor.x, neighbor.y] == 0:
                    liberties.add(neighbor)
        return len(liberties)

    def get_adjacent_positions(self, positions: set[Point], size: int) -> set[Point]:

        adjacent = set()
        for point in positions:
            # Проверяем соседние позиции и добавляем их, если они внутри доски
            if point.x > 0:
                adjacent.add(Point(point.x - 1, point.y))  # Слева
            if point.x < size - 1:
                adjacent.add(Point(point.x + 1, point.y))  # Справа
            if point.y > 0:
                adjacent.add(Point(point.x, point.y - 1))  # Сверху
            if point.y < size - 1:
                adjacent.add(Point(point.x, point.y + 1))  # Снизу
        # Удаляем исходные позиции, чтобы оставить только соседние
        adjacent.difference_update(positions)
        return adjacent
    def is_valid_move(self, col: int, row: int, board: np.ndarray) -> bool:
        if col < 0 or col >= board.shape[0]:
            return False
        if row < 0 or row >= board.shape[0]:
            return False
        return board[col, row] == 0

