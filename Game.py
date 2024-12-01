# Game.py
import random
import sys
import collections
import pygame
from pygame import gfxdraw
import itertools
import numpy as np
from Settings import *
from MainLogic import Game_logic
from typing import List, Tuple, Optional, Dict, Set
from Point import Point
import socket
import select
import traceback  # Для вывода информации об ошибках

class Game:
    def __init__(self, size: int, mode: str):
        self.redo_color = None
        self.redo_flag = None
        self.last_move = None
        self.last_log = None
        self.logic: Game_logic = Game_logic(size)
        self.board: np.ndarray = np.zeros((size, size))
        self.size: int = size
        self.black_turn: bool = False
        self.prisoners: Dict[str, int] = collections.defaultdict(int)
        self.start_points: List[Tuple[int, int]]
        self.end_points: List[Tuple[int, int]]
        self.start_points, self.end_points = self.logic.get_grid_points(self.size)
        self.mode: str = mode
        self.stone_scale_factor: float = self._calculate_scale_factor()
        self.move_log: List[str] = []
        self.esc_button_hovered: bool = False
        self.previous_screen: Optional[pygame.Surface] = None
        self.mouse_pos = Point()  # Исправлена инициализация

        if self.mode == "Играть по сети":
            self.network_role = None
            self.player_color = None
            self.opponent_color = None
            self.conn = None
            self.server_socket = None

    def _calculate_scale_factor(self) -> float:
        return board_scale[self.size]

    def init_pygame(self) -> None:
        pygame.init()
        screen_info = pygame.display.Info()
        screen_width, screen_height = screen_info.current_w, screen_info.current_h
        self.screen = pygame.display.set_mode((screen_width - 10, screen_height - 10))  # Оконный режим для отладки
        self.font = pygame.font.SysFont("Comic Sans", 30)
        self.black_stone_image = pygame.image.load("black_stone.png")
        self.white_stone_image = pygame.image.load("white_stone.png")

        new_size = int(STONE_RADIUS * 2 * self.stone_scale_factor)
        self.black_stone_image = pygame.transform.scale(
            self.black_stone_image, (new_size, new_size))
        self.white_stone_image = pygame.transform.scale(
            self.white_stone_image, (new_size, new_size))

        self.board_offset_x = (screen_width - BOARD_WIDTH) // 2
        self.board_offset_y = (screen_height - BOARD_WIDTH) // 2

        self.previous_screen = pygame.Surface(self.screen.get_size())

        if self.mode == "Играть по сети":
            self.setup_network()

    def clear_screen(self) -> None:
        self.previous_screen.blit(self.screen, (0, 0))
        self.screen.fill(BOARD_BROWN)
        for start_point, end_point in zip(self.start_points, self.end_points):
            start_point = (start_point[0] + self.board_offset_x,
                           start_point[1] + self.board_offset_y)
            end_point = (end_point[0] + self.board_offset_x,
                         end_point[1] + self.board_offset_y)
            pygame.draw.line(self.screen, BLACK, start_point, end_point)
        guide_dots = [3, self.size // 2, self.size - 4]
        for col, row in itertools.product(guide_dots, guide_dots):
            point = Point()
            point = point.colrow_to_point(col, row, self.size)
            point.set_x(point.x + self.board_offset_x)
            point.set_y(point.y + self.board_offset_y)
            gfxdraw.aacircle(self.screen, point.x, point.y, DOT_RADIUS, BLACK)
            gfxdraw.filled_circle(self.screen, point.x, point.y, DOT_RADIUS, BLACK)

    def setup_network(self):
        choice_made = False

        while not choice_made:
            self.screen.fill(WHITE)
            # Создаем кнопки "Создать игру" и "Присоединиться к игре"
            host_button_rect = pygame.Rect(
                self.screen.get_width() // 2 - 150, self.screen.get_height() // 2 - 60, 300, 50)
            join_button_rect = pygame.Rect(
                self.screen.get_width() // 2 - 150, self.screen.get_height() // 2 + 10, 300, 50)

            pygame.draw.rect(self.screen, BUTTON_COLOR, host_button_rect)
            pygame.draw.rect(self.screen, BUTTON_COLOR, join_button_rect)

            host_text = self.font.render("Создать игру", True, BLACK)
            join_text = self.font.render("Присоединиться к игре", True, BLACK)

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
            self.screen.fill(WHITE)
            waiting_text = self.font.render(
                "Ожидание подключения оппонента...", True, BLACK)
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
            self.screen.fill(WHITE)
            connecting_text = self.font.render(
                f"Подключение к {ip_address}...", True, BLACK)
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

    def get_ip_address(self):
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

            self.screen.fill(WHITE)
            prompt_text = self.font.render("Введите IP адрес сервера:", True, BLACK)
            self.screen.blit(prompt_text, (self.screen.get_width() // 2 - 200,
                                           self.screen.get_height() // 2 - 50))
            txt_surface = base_font.render(user_text, True, BLACK)
            width = max(200, txt_surface.get_width() + 10)
            input_rect.w = width
            self.screen.blit(txt_surface, (input_rect.x + 5, input_rect.y + 5))
            pygame.draw.rect(self.screen, color, input_rect, 2)
            pygame.display.flip()

    def _pass_turn(self) -> None:
        self.black_turn = not self.black_turn
        self.draw()

    def _handle_stone_placement(self) -> None:
        point = Point()
        x, y = pygame.mouse.get_pos()
        x -= self.board_offset_x
        y -= self.board_offset_y
        point.set_x(x)
        point.set_y(y)
        col, row = point.point_to_colrow(self.size)
        if not self.logic.is_valid_move(col, row, self.board):
            return

        self.last_move = (col, row)
        self.board[col, row] = 1 if not self.black_turn else 2
        self.redo_flag = False
        move_description = f"{'Белые' if not self.black_turn else 'Чёрные'}: {col + 1},{row + 1}"
        self.move_log.insert(0, move_description)
        if len(self.move_log) > 4:
            self.move_log.pop()

        # Обрабатываем захват камней, если есть
        self._handle_captures(col, row)

        if self.mode == "Играть по сети":
            # Отправляем ход оппоненту
            move_str = f"{col},{row}"
            self.conn.send(move_str.encode())
            self.black_turn = not self.black_turn
            self.draw()
        elif self.mode == "Лёгкий":
            if not self.black_turn:
                self.black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._computer_move()
            else:
                self.black_turn = False
        elif self.mode == "Сложный":
            if not self.black_turn:
                self.black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._smart_computer_move()
            else:
                self.black_turn = False
        else:
            # Если PVP, переключаем ход
            self.black_turn = not self.black_turn

        self.draw()

    def _handle_captures(self, col: int, row: int) -> None:
        self_color = "white" if not self.black_turn else "black"
        other_color = "black" if not self.black_turn else "white"
        capture_happened = False

        # Проверка, не захвачены ли камни противника
        for group in list(self.logic.get_stone_groups(self.board, other_color)):
            if self.logic.stone_group_has_no_liberties(self.board, group):
                capture_happened = True
                for i, j in group:
                    self.board[i, j] = 0
                self.prisoners[self_color] += len(group)

        if not capture_happened:
            group = None
            # Проверка, захватил ли недавно установленный камень свою собственную группу
            for group in self.logic.get_stone_groups(self.board, self_color):
                if (col, row) in group:
                    break
            if group and self.logic.stone_group_has_no_liberties(self.board, group):
                self.board[col, row] = 0

    def _computer_move(self) -> None:
        valid_moves = []
        for col in range(self.size):
            for row in range(self.size):
                if self.logic.is_valid_move(col, row, self.board):
                    valid_moves.append((col, row))

        if valid_moves:
            col, row = random.choice(valid_moves)
            self.board[col, row] = 2
            self._handle_captures(col, row)

            self.move_log.insert(0, f"Чёрные: {col + 1}, {row + 1}")
            self.move_log = self.move_log[:4]

            self.draw()
            self.black_turn = False  # Возвращаем ход игроку

    def _smart_computer_move(self) -> None:
        best_move: Optional[Tuple[int, int]] = None
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
                group = self.logic.get_group(temp_board, (col, row))
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
                    group = self.logic.get_group(temp_board, (col, row))
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

    def _draw_stone_image(self, stone_image: pygame.Surface, board: int) -> None:
        for col, row in zip(*np.where(self.board == board)):
            point = Point()
            point = point.colrow_to_point(col, row, self.size)
            point.set_x(point.x + self.board_offset_x)
            point.set_y(point.y + self.board_offset_y)
            self.screen.blit(stone_image,
                             (point.x - stone_image.get_width() // 2,
                              point.y - stone_image.get_height() // 2))

    def draw(self) -> None:
        self.clear_screen()
        self._draw_stone_image(self.white_stone_image, 1)
        self._draw_stone_image(self.black_stone_image, 2)

        score_msg = f"Захвачено белых камней: {self.prisoners['white']} " \
                    f"Захвачено чёрных камней: {self.prisoners['black']}"
        txt = self.font.render(score_msg, antialias_on, BLACK)
        self.screen.blit(txt, (self.board_offset_x + SCORE_POS[0],
                               self.board_offset_y + SCORE_POS[1]))

        turn_msg1 = f"{'Белые' if not self.black_turn else 'Чёрные'} ходят. " \
                    "Нажмите на левую кнопку мыши, чтобы"
        turn_msg2 = 'поставить камень. Нажмите ESC, чтобы пропустить ход'
        txt1 = self.font.render(turn_msg1, antialias_on, BLACK)
        txt2 = self.font.render(turn_msg2, antialias_on, BLACK)
        self.screen.blit(txt1, (self.board_offset_x + BOARD_BORDER,
                                self.board_offset_y + 10))
        self.screen.blit(txt2, (self.board_offset_x + BOARD_BORDER,
                                self.board_offset_y + 50))

        log_text = "Лог ходов: " + ", ".join(self.move_log[:4])
        log_rendered = self.font.render(log_text, antialias_on, BLACK)
        self.screen.blit(log_rendered, (self.board_offset_x + BOARD_BORDER,
                                        self.board_offset_y + BOARD_WIDTH - BOARD_BORDER + 60))

        esc_button_rect = pygame.Rect(10, 10, 50, 50)
        if self.esc_button_hovered:
            pygame.draw.rect(self.screen, (100, 100, 100), esc_button_rect)
        else:
            pygame.draw.rect(self.screen, (200, 200, 200), esc_button_rect)

        pygame.draw.line(self.screen, BLACK, (15, 15), (55, 55), 3)
        pygame.draw.line(self.screen, BLACK, (15, 55), (55, 15), 3)
        esc_text = self.font.render("ESC", antialias_on, BLACK)
        self.screen.blit(esc_text, (6, 60))

        if self.mode != "Играть по сети":
            self._draw_buttons()

        self._draw_esc_button()
        pygame.display.flip()

    def _draw_esc_button(self) -> None:
        esc_button_rect = pygame.Rect(10, 10, 50, 50)
        button_color = BUTTON_HOVER_COLOR if self.esc_button_hovered else BUTTON_COLOR

        pygame.draw.rect(self.previous_screen, button_color, esc_button_rect)
        pygame.draw.line(self.previous_screen, BLACK, (15, 15), (55, 55), 3)
        pygame.draw.line(self.previous_screen, BLACK, (15, 55), (55, 15), 3)
        esc_text = self.font.render("ESC", antialias_on, BLACK)
        self.previous_screen.blit(esc_text, (6, 60))

        self.screen.blit(self.previous_screen, esc_button_rect, esc_button_rect)
        pygame.display.update(esc_button_rect)

    def update(self) -> Optional[bool]:
        events = pygame.event.get()

        # Обрабатываем события независимо от того, чей сейчас ход
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:
                    return True
            if self.mode == "Играть по сети":
                if self.player_color == ('black' if self.black_turn else 'white'):
                    if event.type == pygame.MOUSEBUTTONUP:
                        if event.button == 1:
                            mouse_x, mouse_y = pygame.mouse.get_pos()

                            # ESC Button
                            esc_button_rect = pygame.Rect(10, 10, 50, 50)
                            if esc_button_rect.collidepoint(mouse_x, mouse_y):
                                return True

                            # Undo и Redo недоступны в сетевой игре
                            self._handle_stone_placement()
            else:
                # Обработка событий для локальной игры
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        mouse_x, mouse_y = pygame.mouse.get_pos()

                        # ESC Button
                        esc_button_rect = pygame.Rect(10, 10, 50, 50)
                        if esc_button_rect.collidepoint(mouse_x, mouse_y):
                            return True

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

                        self._handle_stone_placement()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self._pass_turn()
                    if event.key == pygame.K_u:
                        self.undo()
                    if event.key == pygame.K_r:
                        self.redo()

        if self.mode == "Играть по сети":
            # Обработка сетевых данных
            if self.player_color != ('black' if self.black_turn else 'white'):
                # Ход оппонента
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
        else:
            # Для локальной игры ничего не делаем
            pass

        # Обновление состояния кнопки ESC
        mouse_x, mouse_y = pygame.mouse.get_pos()
        esc_button_rect = pygame.Rect(10, 10, 50, 50)
        if esc_button_rect.collidepoint(mouse_x, mouse_y):
            if not self.esc_button_hovered:
                self.esc_button_hovered = True
                self.draw()
        else:
            if self.esc_button_hovered:
                self.esc_button_hovered = False
                self.draw()

        # Обновляем экран
        pygame.display.flip()
        pygame.time.wait(100)

    def _draw_buttons(self) -> None:
        # Получение размеров экрана для динамического размещения кнопок
        screen_height = self.screen.get_height()

        # Undo Button
        undo_button_rect = pygame.Rect(10, screen_height - 120, 100, 50)
        pygame.draw.rect(self.screen, BUTTON_COLOR, undo_button_rect)
        undo_text = self.font.render("Undo", antialias_on, BLACK)
        self.screen.blit(undo_text, (undo_button_rect.x + 20, undo_button_rect.y + 10))

        # Redo Button
        redo_button_rect = pygame.Rect(10, screen_height - 60, 100, 50)
        pygame.draw.rect(self.screen, BUTTON_COLOR, redo_button_rect)
        redo_text = self.font.render("Redo", antialias_on, BLACK)
        self.screen.blit(redo_text, (redo_button_rect.x + 20, redo_button_rect.y + 10))

    def undo(self):
        if self.last_move is not None:
            if len(self.move_log) > 0:
                self.last_log = self.move_log[0]
            if not self.redo_flag:
                self.move_log.pop(0)
            if self.last_move is not None:
                if self.board[self.last_move[0], self.last_move[1]] == 1:
                    self.black_turn = False
                else:
                    self.black_turn = True
            if self.last_move is not None:
                self.board[self.last_move[0], self.last_move[1]] = 0
            self.redo_flag = True
            self.draw()

    def redo(self):
        if self.redo_flag:
            self.board[self.last_move[0], self.last_move[1]] = 2 if self.black_turn else 1
            self.move_log.insert(0, self.last_log)
            if self.black_turn:
                self.black_turn = False
            else:
                self.black_turn = True
            self.draw()
            self.redo_flag = False
