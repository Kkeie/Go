import random
import sys
import collections
import pygame
from pygame import gfxdraw
import itertools
import numpy as np
from Settings import *  # type: ignore
from MainLogic import Game_logic  # type: ignore
from typing import List, Tuple, Optional, Dict, Set


class Game:
    def __init__(self, size: int, mode: str):
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

    def _calculate_scale_factor(self) -> float:
        return board_scale[self.size]

    def init_pygame(self) -> None:
        pygame.init()
        screen_info = pygame.display.Info()
        screen_width, screen_height = screen_info.current_w, screen_info.current_h
        self.screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
        self.font = pygame.font.SysFont("Comic Sans", 30)
        self.black_stone_image = pygame.image.load("black_stone.png")
        self.white_stone_image = pygame.image.load("white_stone.png")

        new_size = int(STONE_RADIUS * 2 * self.stone_scale_factor)
        self.black_stone_image = pygame.transform.scale(self.black_stone_image, (new_size, new_size))
        self.white_stone_image = pygame.transform.scale(self.white_stone_image, (new_size, new_size))

        self.board_offset_x = (screen_width - BOARD_WIDTH) // 2
        self.board_offset_y = (screen_height - BOARD_WIDTH) // 2

        self.previous_screen = pygame.Surface(self.screen.get_size())

    def clear_screen(self) -> None:
        self.previous_screen.blit(self.screen, (0, 0))
        self.screen.fill(BOARD_BROWN)
        for start_point, end_point in zip(self.start_points, self.end_points):
            start_point = (start_point[0] + self.board_offset_x, start_point[1] + self.board_offset_y)
            end_point = (end_point[0] + self.board_offset_x, end_point[1] + self.board_offset_y)
            pygame.draw.line(self.screen, BLACK, start_point, end_point)
        guide_dots = [3, self.size // 2, self.size - 4]
        for col, row in itertools.product(guide_dots, guide_dots):
            x, y = self.logic.colrow_to_xy(col, row, self.size)
            x += self.board_offset_x
            y += self.board_offset_y
            gfxdraw.aacircle(self.screen, x, y, DOT_RADIUS, BLACK)
            gfxdraw.filled_circle(self.screen, x, y, DOT_RADIUS, BLACK)

    def _pass_turn(self) -> None:
        self.black_turn = not self.black_turn
        self.draw()

    def _handle_stone_placement(self) -> None:
        x, y = pygame.mouse.get_pos()
        x -= self.board_offset_x
        y -= self.board_offset_y
        col, row = self.logic.xy_to_colrow(x, y, self.size)
        if not self.logic.is_valid_move(col, row, self.board):
            return

        # Устанавливаем камень на доске
        self.board[col, row] = 1 if not self.black_turn else 2
        move_description = f"{'Белые' if not self.black_turn else 'Чёрные'}: {col + 1},{row + 1}"
        self.move_log.insert(0, move_description)
        if len(self.move_log) > 4:
            self.move_log.pop()

        # Обрабатываем захват камней, если есть
        self._handle_captures(col, row)

        # Режим игры
        if self.mode == "Лёгкий":
            if not self.black_turn:
                # Ход компьютера в "легком" режиме
                self.black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._computer_move()
            else:
                self.black_turn = False
        elif self.mode == "Сложный":
            if not self.black_turn:
                # Ход компьютера в "сложном" режиме
                self.black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._smart_computer_move()  # Вызов сложного хода компьютера
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
        """
        Симулирует захваты камней противника после размещения камня на временной доске.

        :param temp_board: Копия доски после симуляции хода.
        :param col: Столбец размещения камня.
        :param row: Строка размещения камня.
        :param opponent_color: Цвет камней противника ("white" или "black").
        :return: Количество захваченных камней противника.
        """
        captures = 0
        opponent_groups = self.logic.get_stone_groups(temp_board, opponent_color)
        for group in opponent_groups:
            if self.logic.stone_group_has_no_liberties(temp_board, group):
                captures += len(group)
                for i, j in group:
                    temp_board[i, j] = 0  # Захват камней противника
        return captures

    def _evaluate_move_captures(self, temp_board: np.ndarray, col: int, row: int, color: str) -> int:
        """
        Оценивает количество камней соперника, которые могут быть захвачены этим ходом.
        """
        opponent_color = "white" if color == "black" else "black"
        capture_count = 0

        # Получаем соседние позиции к (col, row)
        adjacent_positions = self.get_adjacent_positions({(col, row)}, self.size)

        # Получаем все группы камней соперника
        opponent_groups = self.logic.get_stone_groups(temp_board, opponent_color)

        # Проверяем только те группы, которые прилегают к позиции хода
        for group in opponent_groups:
            if group & adjacent_positions:  # Пересекаются ли группы с соседними позициями
                if self.logic.stone_group_has_no_liberties(temp_board, group):
                    capture_count += len(group)

        return capture_count

    def _count_liberties(self, temp_board: np.ndarray, col: int, row: int, color: str) -> int:
        """
        Считает количество либертей для группы камней, в которую был сделан ход.
        """
        group = self.logic.get_group(temp_board, (col, row))
        liberties = self.logic.count_liberties(temp_board, group)
        return liberties

    def get_adjacent_positions(self, positions: Set[Tuple[int, int]], size: int) -> Set[Tuple[int, int]]:
        """
        Возвращает все уникальные соседние позиции для множества позиций на доске.

        :param positions: Множество кортежей с координатами (col, row).
        :param size: Размер доски.
        :return: Множество уникальных соседних позиций.
        """
        adjacent = set()

        for col, row in positions:
            # Проверяем каждую из четырех сторон вокруг позиции
            if col > 0:
                adjacent.add((col - 1, row))  # слева
            if col < size - 1:
                adjacent.add((col + 1, row))  # справа
            if row > 0:
                adjacent.add((col, row - 1))  # сверху
            if row < size - 1:
                adjacent.add((col, row + 1))  # снизу

        # Исключаем исходные позиции из списка соседних
        adjacent.difference_update(positions)

        return adjacent

    def _draw_stone_image(self, stone_image: pygame.Surface, board: int) -> None:
        for col, row in zip(*np.where(self.board == board)):
            x, y = self.logic.colrow_to_xy(col, row, self.size)
            x += self.board_offset_x
            y += self.board_offset_y
            self.screen.blit(stone_image, (x - stone_image.get_width() // 2, y - stone_image.get_height() // 2))

    def draw(self) -> None:
        self.clear_screen()
        self._draw_stone_image(self.white_stone_image, 1)
        self._draw_stone_image(self.black_stone_image, 2)

        score_msg = f"Захвачено белых камней: {self.prisoners['white']} Захвачено чёрных камней: {self.prisoners['black']}"
        txt = self.font.render(score_msg, antialias_on, BLACK)
        self.screen.blit(txt, (self.board_offset_x + SCORE_POS[0], self.board_offset_y + SCORE_POS[1]))

        turn_msg1 = f"{'Белые' if not self.black_turn else 'Чёрные'} ходят. Нажмите на левую кнопку мыши, чтобы"
        turn_msg2 = 'поставить камень. Нажмите ESC, чтобы пропустить ход'
        txt1 = self.font.render(turn_msg1, antialias_on, BLACK)
        txt2 = self.font.render(turn_msg2, antialias_on, BLACK)
        self.screen.blit(txt1, (self.board_offset_x + BOARD_BORDER, self.board_offset_y + 10))
        self.screen.blit(txt2, (self.board_offset_x + BOARD_BORDER, self.board_offset_y + 50))

        log_text = "Лог ходов: " + ", ".join(self.move_log[:4])
        log_rendered = self.font.render(log_text, antialias_on, BLACK)
        self.screen.blit(log_rendered,
                         (self.board_offset_x + BOARD_BORDER, self.board_offset_y + BOARD_WIDTH - BOARD_BORDER + 60))

        esc_button_rect = pygame.Rect(10, 10, 50, 50)
        if self.esc_button_hovered:
            pygame.draw.rect(self.screen, (100, 100, 100), esc_button_rect)
        else:
            pygame.draw.rect(self.screen, (200, 200, 200), esc_button_rect)

        pygame.draw.line(self.screen, BLACK, (15, 15), (55, 55), 3)
        pygame.draw.line(self.screen, BLACK, (15, 55), (55, 15), 3)
        esc_text = self.font.render("ESC", antialias_on, BLACK)
        self.screen.blit(esc_text, (6, 60))

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
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    esc_button_rect = pygame.Rect(10, 10, 50, 50)
                    if esc_button_rect.collidepoint(mouse_x, mouse_y):
                        return True
                    self._handle_stone_placement()
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:
                    return True

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

        pygame.time.wait(100)
