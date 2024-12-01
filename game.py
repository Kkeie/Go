# Game.py
import random
import sys
import collections
import pygame
from pygame import gfxdraw
import itertools
import numpy as np

from settings import *
from main_logic import Game_logic
from typing import Optional, Dict, Set, Iterable
from point import Point
from rgb import Rgb
import socket
import select
import traceback


class Game:
    def __init__(self, size: int, mode: str) -> None:
        self.logic: Game_logic = Game_logic(size)
        self.board: np.ndarray = np.zeros((size, size))
        self.size: int = size
        self.black_turn: bool = False
        self.prisoners: Dict[str, int] = collections.defaultdict(int)
        self.start_points: list[Point]
        self.end_points: list[Point]
        self.start_points, self.end_points = self.logic.get_grid_points(self.size)
        self.mode: str = mode
        self.stone_scale_factor: float = self._calculate_scale_factor()
        self.move_log: list[str] = []
        self.esc_button_hovered: bool = False
        self.previous_screen: Optional[pygame.Surface] = None
        self.mouse_pos: Point = Point(0, 0)
        self.drawing = Draw()
        self.last_move = Point(0, 0)
        self.board_that_could_redo = None
        self.move_log_redo = self.move_log.copy()
        self.last_move_board = self.board.copy()
        self.redo_flag = None

        # Параметры для сетевой игры
        if self.mode == "Играть по сети":
            self.network_role = None  # 'host' или 'client'
            self.player_color = None  # 'black' или 'white'
            self.opponent_color = None
            self.conn = None
            self.server_socket = None

    def _calculate_scale_factor(self) -> float:
        return board_scale[self.size]

    def init_pygame(self) -> None:
        pygame.init()
        screen_info: pygame.display.Info = pygame.display.Info()
        screen_width: int = screen_info.current_w
        screen_height: int = screen_info.current_h
        self.screen: pygame.Surface = pygame.display.set_mode((screen_width- 100, screen_height- 100))
        self.font: pygame.font.Font = pygame.font.SysFont("Comic Sans", 30)
        self.black_stone_image: pygame.Surface = pygame.image.load("black_stone.png")
        self.white_stone_image: pygame.Surface = pygame.image.load("white_stone.png")

        new_size: int = int(STONE_RADIUS * 2 * self.stone_scale_factor)
        self.black_stone_image = pygame.transform.scale(self.black_stone_image, (new_size, new_size))
        self.white_stone_image = pygame.transform.scale(self.white_stone_image, (new_size, new_size))

        self.board_offset_x: int = (screen_width - BOARD_WIDTH) // 2
        self.board_offset_y: int = (screen_height - BOARD_WIDTH) // 2

        self.previous_screen = pygame.Surface(self.screen.get_size())

        if self.mode == "Играть по сети":
            self.setup_network()

    def clear_screen(self) -> None:
        assert self.previous_screen is not None
        self.previous_screen.blit(self.screen, (0, 0))
        self.screen.fill((BOARD_BROWN.r, BOARD_BROWN.g, BOARD_BROWN.b))
        for start_point, end_point in zip(self.start_points, self.end_points):
            start_point_screen: Point = Point(
                start_point.x + self.board_offset_x,
                start_point.y + self.board_offset_y,
            )
            end_point_screen: Point = Point(
                end_point.x + self.board_offset_x,
                end_point.y + self.board_offset_y,
            )
            pygame.draw.line(self.screen, (BLACK.r, BLACK.g, BLACK.b),
                             (start_point_screen.x, start_point_screen.y),
                             (end_point_screen.x, end_point_screen.y))

        guide_dots: list[int] = [3, self.size // 2, self.size - 4]
        for col, row in itertools.product(guide_dots, guide_dots):
            point: Point = Point(0, 0)
            point = point.colrow_to_point(col, row, self.size)
            res_point = Point(point.x + self.board_offset_x,
                              point.y + self.board_offset_y)
            gfxdraw.aacircle(self.screen, res_point.x, res_point.y, DOT_RADIUS,
                             (BLACK.r, BLACK.g, BLACK.b))
            gfxdraw.filled_circle(self.screen, res_point.x, res_point.y,
                                  DOT_RADIUS, (BLACK.r, BLACK.g, BLACK.b))

    def setup_network(self):
        choice_made = False

        while not choice_made:
            self.screen.fill((WHITE.r, WHITE.g, WHITE.b))
            # Создаем кнопки "Создать игру" и "Присоединиться к игре"
            host_button_rect = pygame.Rect(
                self.screen.get_width() // 2 - 150, self.screen.get_height() // 2 - 60, 300, 50)
            join_button_rect = pygame.Rect(
                self.screen.get_width() // 2 - 150, self.screen.get_height() // 2 + 10, 300, 50)

            pygame.draw.rect(self.screen, (BUTTON_COLOR.r, BUTTON_COLOR.g, BUTTON_COLOR.b), host_button_rect)
            pygame.draw.rect(self.screen, (BUTTON_COLOR.r, BUTTON_COLOR.g, BUTTON_COLOR.b), join_button_rect)

            host_text = self.font.render("Создать игру", True, (BLACK.r, BLACK.g, BLACK.b))
            join_text = self.font.render("Присоединиться к игре", True, (BLACK.r, BLACK.g, BLACK.b))

            self.screen.blit(host_text, (host_button_rect.x + 50, host_button_rect.y + 10))
            self.screen.blit(join_text, (join_button_rect.x + 20, join_button_rect.y + 10))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        mouse_x, mouse_y = event.pos
                        if host_button_rect.collidepoint(mouse_x, mouse_y):
                            choice_made = True
                            self.network_role = 'host'
                            self.player_color = 'black'
                            self.opponent_color = 'white'
                            self.black_turn = True  # Черные ходят первыми
                            self.start_server()
                        elif join_button_rect.collidepoint(mouse_x, mouse_y):
                            choice_made = True
                            self.network_role = 'client'
                            self.player_color = 'white'
                            self.opponent_color = 'black'
                            self.black_turn = True  # Черные ходят первыми
                            self.connect_to_server()

    def start_server(self):
        # Создаем серверный сокет
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('', 5000))  # Слушаем на всех интерфейсах на порту 5000
        self.server_socket.listen(1)  # Ожидаем одно соединение
        self.server_socket.settimeout(0.1)

        waiting = True
        while waiting:
            self.screen.fill((WHITE.r, WHITE.g, WHITE.b))
            waiting_text = self.font.render(
                "Ожидание подключения оппонента...", True, (BLACK.r, BLACK.g, BLACK.b))
            self.screen.blit(
                waiting_text, (self.screen.get_width() // 2 - 250, self.screen.get_height() // 2))
            pygame.display.flip()

            try:
                self.conn, addr = self.server_socket.accept()
                print("Подключено:", addr)
                waiting = False
            except socket.timeout:
                pass

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

    def connect_to_server(self):
        ip_address = self.get_ip_address()
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.settimeout(0.1)

        connected = False
        while not connected:
            self.screen.fill((WHITE.r, WHITE.g, WHITE.b))
            connecting_text = self.font.render(
                f"Подключение к {ip_address}...", True, (BLACK.r, BLACK.g, BLACK.b))
            self.screen.blit(
                connecting_text, (self.screen.get_width() // 2 - 200, self.screen.get_height() // 2))
            pygame.display.flip()

            try:
                self.conn.connect((ip_address, 5000))
                print("Подключено к серверу")
                connected = True
            except socket.timeout:
                pass
            except Exception as e:
                print("Ошибка подключения:", e)
                pygame.quit()
                sys.exit()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

    def get_ip_address(self) -> str:
        input_active = True
        user_text = ''
        base_font = pygame.font.Font(None, 32)
        input_rect = pygame.Rect(
            self.screen.get_width() // 2 - 100, self.screen.get_height() // 2, 200, 32)
        color_active = pygame.Color('lightskyblue3')
        color_passive = pygame.Color('gray15')
        color = color_active

        while input_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        return user_text
                    elif event.key == pygame.K_BACKSPACE:
                        user_text = user_text[:-1]
                    else:
                        user_text += event.unicode

            self.screen.fill((WHITE.r, WHITE.g, WHITE.b))
            prompt_text = self.font.render("Введите IP адрес сервера:", True, (BLACK.r, BLACK.g, BLACK.b))
            self.screen.blit(prompt_text, (self.screen.get_width() // 2 - 200,
                                           self.screen.get_height() // 2 - 50))
            txt_surface = base_font.render(user_text, True, (BLACK.r, BLACK.g, BLACK.b))
            width = max(200, txt_surface.get_width() + 10)
            input_rect.w = width
            self.screen.blit(txt_surface, (input_rect.x + 5, input_rect.y + 5))
            pygame.draw.rect(self.screen, color, input_rect, 2)
            pygame.display.flip()

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
        self.last_move_board = self.board.copy()
        self.board[col, row] = 1 if not self.black_turn else 2
        self.redo_flag = False
        move_description = f"{'Белые' if not self.black_turn else 'Чёрные'}: {col + 1},{row + 1}"
        self.move_log.insert(0, move_description)
        if len(self.move_log) > 4:
            self.move_log.pop()

        # Обрабатываем захват камней, если есть
        self._handle_captures(col, row)

        # Режим игры
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
            # В сетевом режиме отправляем ход оппоненту
            move_str = f"{col},{row}"
            try:
                self.conn.send(move_str.encode())
                self.black_turn = not self.black_turn
            except Exception as e:
                print("Ошибка при отправке хода:", e)
                pygame.quit()
                sys.exit()

        self.draw()

    def _handle_captures(self, col: int, row: int) -> None:
        self_color: str = "white" if not self.black_turn else "black"
        other_color: str = "black" if not self.black_turn else "white"
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
            self.move_log = self.move_log[:4]

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
                captures = self._simulate_captures(temp_board, col, row, opponent_color="white")

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

    def _simulate_captures(self, temp_board: np.ndarray, col: int, row: int, opponent_color: str) -> int:

        captures = 0
        opponent_groups = self.logic.get_stone_groups(temp_board, opponent_color)
        for group in opponent_groups:
            if self.logic.stone_group_has_no_liberties(temp_board, group):
                captures += len(group)
                for i, j in group:
                    temp_board[i, j] = 0  # Захват камней противника
        return captures

    def draw(self) -> None:
        self.clear_screen()
        self.drawing.draw_stone_image(self.board, self.size,
                                      self.board_offset_x, self.board_offset_y,
                                      self.screen,
                                      self.white_stone_image, board_value=1)
        self.drawing.draw_stone_image(self.board, self.size,
                                      self.board_offset_x, self.board_offset_y,
                                      self.screen,
                                      self.black_stone_image, board_value=2)

        score_msg: str = (
            f"Захвачено белых камней: {self.prisoners['white']} "
            f"Захвачено чёрных камней: {self.prisoners['black']}"
        )
        txt: pygame.Surface = self.font.render(score_msg, True,
                                               (BLACK.r, BLACK.g, BLACK.b))
        self.screen.blit(txt, (self.board_offset_x + SCORE_POS[0],
                               self.board_offset_y + SCORE_POS[1]))

        turn_msg1: str = (
            f"{'Белые' if not self.black_turn else 'Чёрные'} ходят. "
            "Нажмите на левую кнопку мыши, чтобы"
        )
        turn_msg2: str = 'поставить камень. Нажмите ESC, чтобы пропустить ход'
        txt1: pygame.Surface = self.font.render(turn_msg1, True,
                                                (BLACK.r, BLACK.g, BLACK.b))
        txt2: pygame.Surface = self.font.render(turn_msg2, True,
                                                (BLACK.r, BLACK.g, BLACK.b))
        self.screen.blit(txt1, (
            self.board_offset_x + BOARD_BORDER, self.board_offset_y + 10))
        self.screen.blit(txt2, (
            self.board_offset_x + BOARD_BORDER, self.board_offset_y + 50))

        log_text: str = "Лог ходов: " + ", ".join(self.move_log[:4])
        log_rendered: pygame.Surface = self.font.render(log_text, True, (
            BLACK.r, BLACK.g, BLACK.b))
        self.screen.blit(
            log_rendered,
            (self.board_offset_x + BOARD_BORDER,
             self.board_offset_y + BOARD_WIDTH - BOARD_BORDER + 60)
        )

        esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
        if self.esc_button_hovered:
            pygame.draw.rect(self.screen, (100, 100, 100), esc_button_rect)
        else:
            pygame.draw.rect(self.screen, (200, 200, 200), esc_button_rect)

        pygame.draw.line(self.screen, (BLACK.r, BLACK.g, BLACK.b), (15, 15),
                         (55, 55), 3)
        pygame.draw.line(self.screen, (BLACK.r, BLACK.g, BLACK.b), (15, 55),
                         (55, 15), 3)
        esc_text: pygame.Surface = self.font.render("ESC", True,
                                                    (BLACK.r, BLACK.g, BLACK.b))
        self.screen.blit(esc_text, (6, 60))

        self.drawing.draw_esc_button(self.esc_button_hovered,
                                     self.previous_screen, self.font,
                                     self.screen)
        pygame.display.flip()

    def update(self) -> Optional[bool]:
        events: list[pygame.event.Event] = pygame.event.get()
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
                    if esc_button_rect.collidepoint(mouse_x, mouse_y):
                        return True
                    if self.mode != "Играть по сети" or (self.mode == "Играть по сети" and self.player_color == (
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
                    self.undo_move()
                if event.key == pygame.K_r:
                    self.redo_move()

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
        if self.mode == "Играть по сети":
            if self.conn:
                try:
                    ready_to_read, _, _ = select.select([self.conn], [], [], 0)
                    if self.conn in ready_to_read:
                        data = self.conn.recv(1024)
                        if data:
                            move = data.decode().strip()
                            col, row = move.split(',')
                            col = int(col)
                            row = int(row)
                            # Обновляем доску
                            self.board[col, row] = 1 if self.opponent_color == 'white' else 2
                            self._handle_captures(col, row)
                            move_description = f"{'Белые' if self.opponent_color == 'white' else 'Чёрные'}: {col + 1},{row + 1}"
                            self.move_log.insert(0, move_description)
                            if len(self.move_log) > 4:
                                self.move_log.pop()
                            self.black_turn = not self.black_turn
                            self.draw()
                except Exception as e:
                    print("Ошибка при обработке хода оппонента:")
                    traceback.print_exc()
                    pygame.quit()
                    sys.exit()
        self.draw()

        pygame.time.wait(100)

    def undo_move(self):
        if self.mode == GameModes.ONLINE:
            return
        if self.last_move_board is not self.board:
            self.redo_flag = True
            if len(self.move_log) != 0:
                self.move_log_redo = self.move_log.copy()
                self.move_log.pop(0)
            self.board_that_could_redo = self.board.copy()
            self.board = self.last_move_board
            if not self.black_turn:
                self.black_turn = True
            else:
                self.black_turn = False
            self.draw()

    def redo_move(self):
        if self.mode == GameModes.ONLINE:
            return
        if self.board_that_could_redo is not None and self.redo_flag:
            self.board = self.board_that_could_redo
            self.move_log = self.move_log_redo
            if not self.black_turn:
                self.black_turn = True
            else:
                self.black_turn = False
            self.draw()
            self.redo_flag = False


class Draw:
    @staticmethod
    def draw_esc_button(esc_button_hovered, previous_screen, font,
                        screen) -> None:
        esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
        button_color: Rgb = BUTTON_HOVER_COLOR if esc_button_hovered else BUTTON_COLOR
        assert previous_screen is not None  # Для проверки типов
        pygame.draw.rect(previous_screen,
                         (button_color.r, button_color.g, button_color.b),
                         esc_button_rect)
        pygame.draw.line(previous_screen, (BLACK.r, BLACK.g, BLACK.b),
                         (15, 15), (55, 55), 3)
        pygame.draw.line(previous_screen, (BLACK.r, BLACK.g, BLACK.b),
                         (15, 55), (55, 15), 3)
        esc_text: pygame.Surface = font.render("ESC", True,
                                               (BLACK.r, BLACK.g, BLACK.b))
        previous_screen.blit(esc_text, (6, 60))

        screen.blit(previous_screen, esc_button_rect, esc_button_rect)
        pygame.display.update(esc_button_rect)

    @staticmethod
    def draw_stone_image(board, size, board_offset_x, board_offset_y, screen,
                         stone_image: pygame.Surface,
                         board_value: int) -> None:
        for col, row in zip(*np.where(board == board_value)):
            point: Point = Point(0, 0)
            point = point.colrow_to_point(col, row, size)
            point = Point(point.x + board_offset_x, point.y + board_offset_y)
            screen.blit(
                stone_image,
                (point.x - stone_image.get_width() // 2,
                 point.y - stone_image.get_height() // 2)
            )
