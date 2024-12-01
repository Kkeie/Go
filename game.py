# game.py

import collections
import random
import sys
from typing import Optional, Dict

import numpy as np
import pygame
from point import Point
from main_logic import Game_logic
from networker import NetworkManager
from renderer import Renderer
from settings import *

class Game:
    def __init__(self, size: int, mode: str) -> None:
        self.logic: Game_logic = Game_logic(size)
        self.board: np.ndarray = np.zeros((size, size))
        self.size: int = size
        self.black_turn: bool = False
        self.prisoners: Dict[str, int] = collections.defaultdict(int)
        self.start_points, self.end_points = self.logic.get_grid_points(self.size)
        self.mode: str = mode
        self.move_log: list[str] = []
        self.esc_button_hovered: bool = False
        self.last_move = Point(0, 0)
        self.redo_flag = None
        self.last_log = None  # Для функциональности Undo/Redo

        self.screen = None
        self.font = None
        self.board_offset_x = None
        self.board_offset_y = None

        self.renderer = None

        if self.mode == GameModes.ONLINE:
            self.network_manager = NetworkManager(self.mode, None, None)
        else:
            self.network_manager = None

    def _calculate_scale_factor(self) -> float:
        return board_scale[self.size]

    def init_pygame(self) -> None:
        pygame.init()
        screen_info: pygame.display.Info = pygame.display.Info()
        screen_width: int = screen_info.current_w
        screen_height: int = screen_info.current_h
        self.screen: pygame.Surface = pygame.display.set_mode((screen_width, screen_height))
        self.font: pygame.font.Font = pygame.font.SysFont("Comic Sans", 30)

        self.board_offset_x: int = (screen_width - BOARD_WIDTH) // 2
        self.board_offset_y: int = (screen_height - BOARD_WIDTH) // 2

        # Инициализируем Renderer
        self.renderer = Renderer(self.size, self.screen, self.board_offset_x, self.board_offset_y, self.font)

        if self.mode == GameModes.ONLINE:
            self.network_manager.font = self.font
            self.network_manager.screen = self.screen
            self.network_manager.setup_network()
            self.player_color = self.network_manager.player_color
            self.opponent_color = self.network_manager.opponent_color
            self.black_turn = True  # Черные ходят первыми

    def _pass_turn(self) -> None:
        self.black_turn = not self.black_turn
        self.draw()

    def _handle_stone_placement(self) -> None:
        x, y = pygame.mouse.get_pos()
        x -= self.board_offset_x
        y -= self.board_offset_y
        point = Point(x, y)
        col, row = point.point_to_colrow(self.size)
        if not self.logic.is_valid_move(col, row, self.board):
            return
        self.last_move = Point(col, row)
        self.board[col, row] = 1 if not self.black_turn else 2
        self.redo_flag = False
        move_description = f"{'Белые' if not self.black_turn else 'Чёрные'}: {col + 1},{row + 1}"
        self.move_log.insert(0, move_description)
        if len(self.move_log) > 4:
            self.move_log.pop()

        # Обрабатываем захват камней, если есть
        self._handle_captures(col, row)

        # Режимы игры
        if self.mode == GameModes.EASY:
            if not self.black_turn:
                # Ход компьютера в "легком" режиме
                self.black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._computer_move()
            else:
                self.black_turn = False
        elif self.mode == GameModes.DIFFICULTY:
            if not self.black_turn:
                # Ход компьютера в "сложном" режиме
                self.black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._smart_computer_move()  # Вызов сложного хода компьютера
            else:
                self.black_turn = False
        elif self.mode == GameModes.PVP:
            # Если PVP, переключаем ход
            self.black_turn = not self.black_turn
        elif self.mode == GameModes.ONLINE:
            # Отправляем ход оппоненту
            move_str = f"{col},{row}"
            self.network_manager.send_move(move_str)
            self.black_turn = not self.black_turn
            self.draw()

        self.draw()

    def _handle_captures(self, col: int, row: int) -> None:
        self_color: str = 'white' if not self.black_turn else 'black'
        other_color: str = 'black' if not self.black_turn else 'white'
        capture_happened: bool = False

        # Проверка, не захвачены ли камни противника
        for group in self.logic.get_stone_groups(self.board, other_color):
            if self.logic.stone_group_has_no_liberties(self.board, group):
                capture_happened = True
                for point in group:
                    self.board[point.x, point.y] = 0
                self.prisoners[self_color] += len(group)

        if not capture_happened:
            group = None
            # Проверка, захватил ли недавно установленный камень свою собственную группу
            for current_group in self.logic.get_stone_groups(self.board, self_color):
                if Point(col, row) in current_group:
                    group = current_group
                    break
            if group and self.logic.stone_group_has_no_liberties(self.board, group):
                self.board[col, row] = 0

    def _computer_move(self) -> None:
        valid_moves: list[Point] = []
        for col in range(self.size):
            for row in range(self.size):
                if self.logic.is_valid_move(col, row, self.board):
                    valid_moves.append(Point(col, row))

        if valid_moves:
            chosen_move: Point = random.choice(valid_moves)
            chosen_col, chosen_row = chosen_move.x, chosen_move.y
            self.board[chosen_col, chosen_row] = 2
            self._handle_captures(chosen_col, chosen_row)

            self.move_log.insert(0,
                                 f"Чёрные: {chosen_col + 1}, {chosen_row + 1}")
            if len(self.move_log) > 4:
                self.move_log.pop()

            self.draw()
            self.black_turn = False  # Возвращаем ход игроку

    def _smart_computer_move(self) -> None:
        best_move: Optional[tuple[int, int]] = None
        best_score: int = -1  # Начальная оценка

        # Перебор всех возможных ходов
        for col in range(self.size):
            for row in range(self.size):
                if not self.logic.is_valid_move(col, row, self.board):
                    continue  # Пропускаем недопустимые ходы

                # Симуляция хода: копирование доски и размещение камня
                temp_board = self.board.copy()
                temp_board[col, row] = 2  # Черный камень

                # Симуляция захватов камней противника
                captures = self._simulate_captures(temp_board, opponent_color="white")

                # Подсчет либертей для группы камней после хода
                group = self.logic.get_group(temp_board, Point(col, row))
                liberties = self.logic.count_liberties(temp_board, group)

                # Оценка хода: приоритет захватов, затем либертей
                score = captures * 10 + liberties  # Вес захватов больше, чем либертей

                # Выбор хода с наивысшей оценкой
                if score > best_score:
                    best_score = score
                    best_move = (col, row)

        # Если ни один ход не привел к захватам, выбираем ход с максимальными либертями
        if best_move is None:
            max_liberties = -1
            for col in range(self.size):
                for row in range(self.size):
                    if not self.logic.is_valid_move(col, row, self.board):
                        continue

                    # Симуляция хода
                    temp_board = self.board.copy()
                    temp_board[col, row] = 2  # Черный камень

                    # Подсчет либертей для группы камней после хода
                    group = self.logic.get_group(temp_board, Point(col, row))
                    liberties = self.logic.count_liberties(temp_board, group)

                    # Выбор хода с наибольшим количеством либертей
                    if liberties > max_liberties:
                        max_liberties = liberties
                        best_move = (col, row)

        # Если ни один из критериев не сработал, выбираем случайный допустимый ход
        if best_move is None:
            valid_moves = [(col, row) for col in range(self.size) for row in range(self.size)
                           if self.logic.is_valid_move(col, row, self.board)]
            if valid_moves:
                best_move = random.choice(valid_moves)

        # Совершение выбранного хода
        if best_move:
            col, row = best_move
            self.board[col, row] = 2  # Размещение черного камня
            self._handle_captures(col, row)  # Обработка захватов
            self.move_log.insert(0, f"Чёрные: {col + 1}, {row + 1}")
            if len(self.move_log) > 4:
                self.move_log.pop()
            self.draw()  # Обновление экрана
            self.black_turn = False  # Передача хода игроку
        else:
            print("Компьютер не смог найти ход.")  # Для отладки

    def _simulate_captures(self, temp_board: np.ndarray, opponent_color: str) -> int:
        captures = 0
        opponent_groups = self.logic.get_stone_groups(temp_board, opponent_color)
        for group in opponent_groups:
            if self.logic.stone_group_has_no_liberties(temp_board, group):
                captures += len(group)
                for i, j in group:
                    temp_board[i, j] = 0  # Захват камней противника
        return captures

    def draw(self) -> None:
        self.renderer.draw(
            self.board,
            self.prisoners,
            self.black_turn,
            self.move_log,
            self.esc_button_hovered,
            self.start_points,
            self.end_points,
            self.mode
        )

    def update(self) -> Optional[bool]:
        events: list[pygame.event.Event] = pygame.event.get()
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
                    # Undo Button
                    undo_button_rect = pygame.Rect(
                        10, self.screen.get_height() - 120, 100, 50)
                    if undo_button_rect.collidepoint(mouse_x, mouse_y):
                        self.undo()

                    # Redo Button
                    redo_button_rect = pygame.Rect(
                        10, self.screen.get_height() - 60, 100, 50)
                    if redo_button_rect.collidepoint(mouse_x, mouse_y):
                        self.redo()
                    if esc_button_rect.collidepoint(mouse_x, mouse_y):
                        return True
                    if self.mode != GameModes.ONLINE or (self.mode == GameModes.ONLINE and self.player_color == (
                            'black' if self.black_turn else 'white')):
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
                    self.undo()
                if event.key == pygame.K_r:
                    self.redo()

        mouse_x: int
        mouse_y: int
        mouse_x, mouse_y = pygame.mouse.get_pos()
        esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
        if esc_button_rect.collidepoint(mouse_x, mouse_y):
            if not self.esc_button_hovered:
                self.esc_button_hovered = True
                self.draw()
        else:
            if self.esc_button_hovered:
                self.esc_button_hovered = False
                self.draw()

        # Обработка сетевых данных
        if self.mode == GameModes.ONLINE:
            if self.network_manager.conn:
                move = self.network_manager.receive_move()
                if move:
                    col, row = move
                    # Обновляем доску
                    self.board[col, row] = 2 if self.opponent_color == 'black' else 1
                    self._handle_captures(col, row)
                    move_description = f"{'Белые' if self.opponent_color == 'white' else 'Чёрные'}: {col + 1},{row + 1}"
                    self.move_log.insert(0, move_description)
                    if len(self.move_log) > 4:
                        self.move_log.pop()
                    self.black_turn = not self.black_turn
                    self.draw()

        self.draw()

        pygame.time.wait(100)

    def undo(self):
        if self.last_move is not None:
            if len(self.move_log) > 0:
                self.last_log = self.move_log[0]
            if not self.redo_flag:
                self.move_log.pop(0)
            if self.last_move is not None:
                if self.board[self.last_move.x, self.last_move.y] == 1:
                    self.black_turn = False
                else:
                    self.black_turn = True
            if self.last_move is not None:
                self.board[self.last_move.x, self.last_move.y] = 0
            self.redo_flag = True
            self.draw()

    def redo(self):
        if self.redo_flag:
            self.board[self.last_move.x, self.last_move.y] = 2 if self.black_turn else 1
            self.move_log.insert(0, self.last_log)
            if self.black_turn:
                self.black_turn = False
            else:
                self.black_turn = True
            self.draw()
            self.redo_flag = False
