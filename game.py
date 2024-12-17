import collections
import random
import sys
import numpy as np
import pygame
from main_logic import game_logic
from networker import NetworkManager
from point import Point
from renderer import Renderer
from settings import *


class Game:
    def __init__(self, size: int, mode: str) -> None:
        self._logic: game_logic = game_logic(size)
        self._board: np.ndarray = np.zeros((size, size))
        self._size: int = size
        self._black_turn: bool = False
        self._prisoners: collections.defaultdict = collections.defaultdict(int)
        self._start_points, self._end_points = self._logic.get_grid_points(self._size)
        self._mode: str = mode
        self._move_log: list[str] = []
        self._esc_button_hovered: bool = False
        self._last_move: Point = Point(0, 0)
        self._redo_flag: bool = False
        self._last_log: str | None = None

        self._screen: pygame.Surface | None = None
        self._font: pygame.font.Font | None = None
        self._board_offset_x: int | None = None
        self._board_offset_y: int | None = None

        self._renderer: Renderer | None = None

        if self._mode == GameModes.ONLINE:
            self._network_manager: NetworkManager | None = NetworkManager(self._mode, None, None)
        else:
            self._network_manager: NetworkManager | None = None

        self._player_color: str | None = None
        self._opponent_color: str | None = None

    def _calculate_scale_factor(self) -> float:
        return board_scale[self._size]

    def init_pygame(self) -> None:
        pygame.init()
        screen_info: pygame.display.Info = pygame.display.Info()
        screen_width: int = screen_info.current_w
        screen_height: int = screen_info.current_h
        self._screen: pygame.Surface = pygame.display.set_mode((screen_width, screen_height))
        self._font: pygame.font.Font = pygame.font.SysFont("Comic Sans", 30)

        self._board_offset_x: int = (screen_width - BOARD_WIDTH) // 2
        self._board_offset_y: int = (screen_height - BOARD_WIDTH) // 2

        # Инициализируем Renderer
        self._renderer = Renderer(self._size, self._screen, self._board_offset_x, self._board_offset_y, self._font)

        if self._mode == GameModes.ONLINE:
            self._network_manager._font = self._font
            self._network_manager._screen = self._screen
            self._network_manager.setup_network()
            self._player_color = self._network_manager._player_color
            self._opponent_color = self._network_manager._opponent_color
            self._black_turn = True  # Черные ходят первыми

    def _pass_turn(self) -> None:
        self._black_turn = not self._black_turn
        self.draw()

    def _handle_stone_placement(self) -> None:
        x, y = pygame.mouse.get_pos()
        x -= self._board_offset_x
        y -= self._board_offset_y
        point = Point(x, y)
        col, row = self._logic.point_to_colrow(point)
        if not self._logic.is_valid_move(col, row, self._board):
            return
        self._last_move = Point(col, row)
        self._board[col, row] = 1 if not self._black_turn else 2
        self._redo_flag = False
        move_description = f"{'Белые' if not self._black_turn else 'Чёрные'}: {col + 1},{row + 1}"
        self._move_log.insert(0, move_description)
        if len(self._move_log) > 4:
            self._move_log.pop()

        # Обрабатываем захват камней, если есть
        self._handle_captures(col, row)

        # Режимы игры
        if self._mode == GameModes.EASY:
            if not self._black_turn:
                # Ход компьютера в "легком" режиме
                self._black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._computer_move()
            else:
                self._black_turn = False
        elif self._mode == GameModes.DIFFICULTY:
            if not self._black_turn:
                # Ход компьютера в "сложном" режиме
                self._black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._smart_computer_move()  # Вызов сложного хода компьютера
            else:
                self._black_turn = False
        elif self._mode == GameModes.PVP:
            # Если PVP, переключаем ход
            self._black_turn = not self._black_turn
        elif self._mode == GameModes.ONLINE:
            # Отправляем ход оппоненту
            move_str = f"{col},{row}"
            self._network_manager.send_move(move_str)
            self._black_turn = not self._black_turn
            self.draw()

        self.draw()

    def _handle_captures(self, col: int, row: int) -> None:
        self_color: str = 'white' if not self._black_turn else 'black'
        other_color: str = 'black' if not self._black_turn else 'white'
        capture_happened: bool = False

        # Проверка, не захвачены ли камни противника
        for group in self._logic.get_stone_groups(self._board, other_color):
            if self._logic.stone_group_has_no_liberties(self._board, group):
                capture_happened = True
                for point in group:
                    self._board[point.x, point.y] = 0
                self._prisoners[self_color] += len(group)

        if not capture_happened:
            group = None
            # Проверка, захватил ли недавно установленный камень свою собственную группу
            for current_group in self._logic.get_stone_groups(self._board, self_color):
                if Point(col, row) in current_group:
                    group = current_group
                    break
            if group and self._logic.stone_group_has_no_liberties(self._board, group):
                self._board[col, row] = 0

    def _computer_move(self) -> None:
        valid_moves: list[Point] = []
        for col in range(self._size):
            for row in range(self._size):
                if self._logic.is_valid_move(col, row, self._board):
                    valid_moves.append(Point(col, row))

        if valid_moves:
            chosen_move: Point = random.choice(valid_moves)
            chosen_col, chosen_row = chosen_move.x, chosen_move.y
            self._board[chosen_col, chosen_row] = 2
            self._handle_captures(chosen_col, chosen_row)

            self._move_log.insert(0, f"Чёрные: {chosen_col + 1}, {chosen_row + 1}")
            if len(self._move_log) > 4:
                self._move_log.pop()

            self.draw()
            self._black_turn = False  # Возвращаем ход игроку

    def _smart_computer_move(self) -> None:
        best_move: tuple[int, int] | None = None
        best_score: int = -1  # Начальная оценка

        # Перебор всех возможных ходов
        for col in range(self._size):
            for row in range(self._size):
                if not self._logic.is_valid_move(col, row, self._board):
                    continue  # Пропускаем недопустимые ходы

                # Симуляция хода: копирование доски и размещение камня
                temp_board = self._board.copy()
                temp_board[col, row] = 2  # Черный камень

                # Симуляция захватов камней противника
                captures = self._simulate_captures(temp_board, opponent_color="white")

                # Подсчет либертей для группы камней после хода
                group = self._logic.get_group(temp_board, Point(col, row))
                liberties = self._logic.count_liberties(temp_board, group)

                # Оценка хода: приоритет захватов, затем либертей
                score = captures * 10 + liberties  # Вес захватов больше, чем либертей

                # Выбор хода с наивысшей оценкой
                if score > best_score:
                    best_score = score
                    best_move = (col, row)

        # Если ни один ход не привел к захватам, выбираем ход с максимальными либертями
        if best_move is None:
            max_liberties = -1
            for col in range(self._size):
                for row in range(self._size):
                    if not self._logic.is_valid_move(col, row, self._board):
                        continue

                    # Симуляция хода
                    temp_board = self._board.copy()
                    temp_board[col, row] = 2  # Черный камень

                    # Подсчет либертей для группы камней после хода
                    group = self._logic.get_group(temp_board, Point(col, row))
                    liberties = self._logic.count_liberties(temp_board, group)

                    # Выбор хода с наибольшим количеством либертей
                    if liberties > max_liberties:
                        max_liberties = liberties
                        best_move = (col, row)

        # Если ни один из критериев не сработал, выбираем случайный допустимый ход
        if best_move is None:
            valid_moves = [(col, row) for col in range(self._size) for row in range(self._size)
                           if self._logic.is_valid_move(col, row, self._board)]
            if valid_moves:
                best_move = random.choice(valid_moves)

        # Совершение выбранного хода
        if best_move:
            col, row = best_move
            self._board[col, row] = 2  # Размещение черного камня
            self._handle_captures(col, row)  # Обработка захватов
            self._move_log.insert(0, f"Чёрные: {col + 1}, {row + 1}")
            if len(self._move_log) > 4:
                self._move_log.pop()
            self.draw()  # Обновление экрана
            self._black_turn = False  # Передача хода игроку
        else:
            print("Компьютер не смог найти ход.")  # Для отладки

    def _simulate_captures(self, temp_board: np.ndarray, opponent_color: str) -> int:
        captures = 0
        opponent_groups = self._logic.get_stone_groups(temp_board, opponent_color)
        for group in opponent_groups:
            if self._logic.stone_group_has_no_liberties(temp_board, group):
                captures += len(group)
                for i, j in group:
                    temp_board[i, j] = 0  # Захват камней противника
        return captures

    def draw(self) -> None:
        self._renderer.draw(
            self._board,
            self._prisoners,
            self._black_turn,
            self._move_log,
            self._esc_button_hovered,
            self._start_points,
            self._end_points,
            self._mode
        )

    def update(self) -> bool | None:
        events: list[pygame.event.Event] = pygame.event.get()
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
                    # Undo Button
                    undo_button_rect = pygame.Rect(
                        10, self._screen.get_height() - 120, 100, 50)
                    if undo_button_rect.collidepoint(mouse_x, mouse_y):
                        self._undo()

                    # Redo Button
                    redo_button_rect = pygame.Rect(
                        10, self._screen.get_height() - 60, 100, 50)
                    if redo_button_rect.collidepoint(mouse_x, mouse_y):
                        self._redo()
                    if esc_button_rect.collidepoint(mouse_x, mouse_y):
                        return True
                    if self._mode != GameModes.ONLINE or (self._mode == GameModes.ONLINE and self._player_color == (
                            'black' if self._black_turn else 'white')):
                        self._handle_stone_placement()
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:
                    return True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self._pass_turn()
                if event.key == pygame.K_u:
                    self._undo()
                if event.key == pygame.K_r:
                    self._redo()

        mouse_x: int
        mouse_y: int
        mouse_x, mouse_y = pygame.mouse.get_pos()
        esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
        if esc_button_rect.collidepoint(mouse_x, mouse_y):
            if not self._esc_button_hovered:
                self._esc_button_hovered = True
                self.draw()
        else:
            if self._esc_button_hovered:
                self._esc_button_hovered = False
                self.draw()

        # Обработка сетевых данных
        if self._mode == GameModes.ONLINE:
            if self._network_manager and self._network_manager._conn:
                move = self._network_manager.receive_move()
                if move:
                    col, row = move.x, move.y
                    # Обновляем доску
                    self._board[col, row] = 2 if self._opponent_color == 'black' else 1
                    self._handle_captures(col, row)
                    move_description = f"{'Белые' if self._opponent_color == 'white' else 'Чёрные'}: {col + 1},{row + 1}"
                    self._move_log.insert(0, move_description)
                    if len(self._move_log) > 4:
                        self._move_log.pop()
                    self._black_turn = not self._black_turn
                    self.draw()

        self.draw()

        pygame.time.wait(100)

    def _undo(self) -> None:
        if self._last_move is not None:
            if len(self._move_log) > 0:
                self._last_log = self._move_log[0]
            if not self._redo_flag:
                self._move_log.pop(0)
            if self._last_move is not None:
                if self._board[self._last_move.x, self._last_move.y] == 1:
                    self._black_turn = False
                else:
                    self._black_turn = True
            if self._last_move is not None:
                self._board[self._last_move.x, self._last_move.y] = 0
            self._redo_flag = True
            self.draw()

    def _redo(self) -> None:
        if self._redo_flag and self._last_log is not None and self._last_move is not None:
            self._board[self._last_move.x, self._last_move.y] = 2 if self._black_turn else 1
            self._move_log.insert(0, self._last_log)
            if self._black_turn:
                self._black_turn = False
            else:
                self._black_turn = True
            self.draw()
            self._redo_flag = False
