import itertools
import networkx as nx
import numpy as np
from typing import List, Tuple, Set, Iterable
from Settings import *

class Game_logic:
    def get_grid_points(self, size: int) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        start_points, end_points = [], []
        xs = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
        ys = np.full(size, BOARD_BORDER)
        start_points.extend(zip(xs, ys))
        xs = np.full(size, BOARD_BORDER)
        ys = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
        start_points.extend(zip(xs, ys))
        xs = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
        ys = np.full(size, BOARD_WIDTH - BOARD_BORDER)
        end_points.extend(zip(xs, ys))
        xs = np.full(size, BOARD_WIDTH - BOARD_BORDER)
        ys = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
        end_points.extend(list(zip(xs, ys)))
        return start_points, end_points

    def xy_to_colrow(self, x: float, y: float, size: int) -> Tuple[int, int]:
        inc = (BOARD_WIDTH - 2 * BOARD_BORDER) / (size - 1)
        x_dist = x - BOARD_BORDER
        y_dist = y - BOARD_BORDER
        col = round(x_dist / inc)
        row = round(y_dist / inc)
        return col, row

    def colrow_to_xy(self, col: int, row: int, size: int) -> Tuple[int, int]:
        inc = (BOARD_WIDTH - 2 * BOARD_BORDER) / (size - 1)
        x = int(BOARD_BORDER + col * inc)
        y = int(BOARD_BORDER + row * inc)
        return x, y

    def stone_group_has_no_liberties(self, board: np.ndarray, group: Set[Tuple[int, int]]) -> bool:
        for x, y in group:
            if x > 0 and board[x - 1, y] == 0:
                return False
            if y > 0 and board[x, y - 1] == 0:
                return False
            if x < board.shape[0] - 1 and board[x + 1, y] == 0:
                return False
            if y < board.shape[0] - 1 and board[x, y + 1] == 0:
                return False
        return True

    def get_stone_groups(self, board: np.ndarray, color: str) -> Iterable[Set[Tuple[int, int]]]:
        size = board.shape[0]
        color_code = 1 if color == "white" else 2
        xs, ys = np.where(board == color_code)
        graph = nx.grid_graph(dim=[size, size])
        stones = set(zip(xs, ys))
        all_spaces = set(itertools.product(range(size), range(size)))
        stones_to_remove = all_spaces - stones
        graph.remove_nodes_from(stones_to_remove)
        return nx.connected_components(graph)

    def is_valid_move(self, col: int, row: int, board: np.ndarray) -> bool:
        if col < 0 or col >= board.shape[0]:
            return False
        if row < 0 or row >= board.shape[0]:
            return False
        return board[col, row] == 0



