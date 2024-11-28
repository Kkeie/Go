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


class Game:
    def __init__(self, size: int, mode: str) -> None:
        self.logic: Game_logic = Game_logic(size)
        self.board: np.ndarray = np.zeros((size, size))
        self.size: int = size
        self.black_turn: bool = False
        self.prisoners: Dict[str, int] = collections.defaultdict(int)
        self.start_points: list[Point]
        self.end_points: list[Point]
        self.start_points, self.end_points = self.logic.get_grid_points(
            self.size)
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

    def _calculate_scale_factor(self) -> float:
        return board_scale[self.size]

    def init_pygame(self) -> None:
        pygame.init()
        screen_info: pygame.display.Info = pygame.display.Info()
        screen_width: int = screen_info.current_w
        screen_height: int = screen_info.current_h
        self.screen: pygame.Surface = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
        self.font: pygame.font.Font = pygame.font.SysFont("Comic Sans", 30)
        self.black_stone_image: pygame.Surface = pygame.image.load(
            "black_stone.png")
        self.white_stone_image: pygame.Surface = pygame.image.load(
            "white_stone.png")

        new_size: int = int(STONE_RADIUS * 2 * self.stone_scale_factor)
        self.black_stone_image = pygame.transform.scale(self.black_stone_image,
                                                        (new_size, new_size))
        self.white_stone_image = pygame.transform.scale(self.white_stone_image,
                                                        (new_size, new_size))

        self.board_offset_x: int = (screen_width - BOARD_WIDTH) // 2
        self.board_offset_y: int = (screen_height - BOARD_WIDTH) // 2

        self.previous_screen = pygame.Surface(self.screen.get_size())

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

    def _pass_turn(self) -> None:
        self.black_turn = not self.black_turn
        self.draw()

    def _handle_stone_placement(self) -> None:
        x = 0
        y = 0
        if pygame.mouse.get_pressed():
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
        if self.mode == GameModes.EASY.value:
            if not self.black_turn:
                # Ход компьютера в "легком" режиме
                self.black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._computer_move()
            else:
                self.black_turn = False
        elif self.mode == GameModes.DIFFICULTY.value:
            if not self.black_turn:
                # Ход компьютера в "сложном" режиме
                self.black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._smart_computer_move()  # Вызов сложного хода компьютера
            else:
                self.black_turn = False
        elif self.mode == GameModes.PVP.value:
            # Если PVP, переключаем ход
            self.black_turn = not self.black_turn

        self.draw()

    def _handle_captures(self, col: int, row: int) -> None:
        self_color: str = "white" if not self.black_turn else "black"
        other_color: str = "black" if not self.black_turn else "white"
        capture_happened: bool = False

        # Check if opponent's stones are captured
        for group in self.logic.get_stone_groups(self.board, other_color):
            if self.logic.stone_group_has_no_liberties(self.board, group):
                capture_happened = True
                for point in group:
                    self.board[point.x, point.y] = 0
                self.prisoners[self_color] += len(group)

        if not capture_happened:
            group = None
            # Check if the recently placed stone's group has no liberties
            for current_group in self.logic.get_stone_groups(self.board,
                                                             self_color):
                if Point(col, row) in current_group:
                    group = current_group
                    break
            if group and self.logic.stone_group_has_no_liberties(self.board,
                                                                 group):
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
            self.black_turn = False  # Return turn to the player

    def _smart_computer_move(self) -> None:
        best_move: Optional[Point] = None
        best_score: int = -1  # Initial score

        # Iterate through all possible moves
        for col in range(self.size):
            for row in range(self.size):
                if not self.logic.is_valid_move(col, row, self.board):
                    continue  # Skip invalid moves

                # Simulate the move: copy the board and place the stone
                temp_board: np.ndarray = self.board.copy()
                temp_board[col, row] = 2  # Black stone

                # Simulate capturing opponent's stones
                captures: int = self._simulate_captures(temp_board, opponent_color="white")

                # Count liberties for the group after the move
                group: Set[Point] = self.logic.get_group(temp_board,
                                                         Point(col, row))
                liberties: int = self.logic.count_liberties(temp_board, group)

                # Evaluate the move: prioritize captures, then liberties
                score: int = captures * 10 + liberties  # Capture weight higher than liberties

                # Choose the move with the highest score
                if score > best_score:
                    best_score = score
                    best_move = Point(col, row)

        # If no move resulted in captures, choose the move with maximum liberties
        if best_move is None:
            max_liberties: int = -1
            for col in range(self.size):
                for row in range(self.size):
                    if not self.logic.is_valid_move(col, row, self.board):
                        continue

                    # Simulate the move
                    temp_board: np.ndarray = self.board.copy()
                    temp_board[col, row] = 2  # Black stone

                    # Count liberties for the group after the move
                    group: Set[Point] = self.logic.get_group(temp_board,
                                                             Point(col, row))
                    liberties: int = self.logic.count_liberties(temp_board,
                                                                group)

                    # Select the move with the highest number of liberties
                    if liberties > max_liberties:
                        max_liberties = liberties
                        best_move = Point(col, row)

        # If no criteria matched, choose a random valid move
        if best_move is None:
            valid_moves: list[Point] = [
                Point(col, row) for col in range(self.size) for row in
                range(self.size)
                if self.logic.is_valid_move(col, row, self.board)
            ]
            if valid_moves:
                best_move = random.choice(valid_moves)

        # Make the chosen move
        if best_move:
            chosen_col, chosen_row = best_move.x, best_move.y
            self.board[chosen_col, chosen_row] = 2  # Place black stone
            self._handle_captures(chosen_col, chosen_row)  # Handle captures
            self.move_log.insert(0,
                                 f"Чёрные: {chosen_col + 1}, {chosen_row + 1}")
            if len(self.move_log) > 4:
                self.move_log.pop()
            self.draw()  # Update the screen
            self.black_turn = False  # Return turn to the player
        else:
            print("Компьютер не смог найти ход.")  # For debugging

    def _simulate_captures(self, temp_board: np.ndarray, opponent_color: str) -> int:
        captures: int = 0
        opponent_groups: Iterable[Set[Point]] = self.logic.get_stone_groups(
            temp_board, opponent_color)
        for group in opponent_groups:
            if self.logic.stone_group_has_no_liberties(temp_board, group):
                captures += len(group)
                for point in group:
                    temp_board[
                        point.x, point.y] = 0  # Capture opponent's stones
        return captures

    def _evaluate_move_captures(self, temp_board: np.ndarray, col: int,
                                row: int, color: str) -> int:
        opponent_color: str = "white" if color == "black" else "black"
        capture_count: int = 0

        # Get adjacent positions to (col, row)
        adjacent_positions: Set[Point] = self.get_adjacent_positions(
            {Point(col, row)}, self.size)

        # Get all opponent's stone groups
        opponent_groups: Iterable[set[Point]] = self.logic.get_stone_groups(
            temp_board, opponent_color)

        # Check only those groups that are adjacent to the move position
        for group in opponent_groups:
            if group & adjacent_positions:  # Check if groups intersect with adjacent positions
                if self.logic.stone_group_has_no_liberties(temp_board, group):
                    capture_count += len(group)

        return capture_count

    def _count_liberties(self, temp_board: np.ndarray, col: int, row: int) -> int:
        groups: Set[Point] = self.logic.get_group(temp_board, Point(col, row))
        liberties: int = self.logic.count_liberties(temp_board, groups)
        return liberties

    def get_adjacent_positions(self, positions: Set[Point], size: int) -> set[Point]:
        adjacent: Set[Point] = set()

        for point in positions:
            # Check each of the four sides around the position
            if point.x > 0:
                adjacent.add(Point(point.x - 1, point.y))  # Left
            if point.x < size - 1:
                adjacent.add(Point(point.x + 1, point.y))  # Right
            if point.y > 0:
                adjacent.add(Point(point.x, point.y - 1))  # Top
            if point.y < size - 1:
                adjacent.add(Point(point.x, point.y + 1))  # Bottom

        # Remove the original positions from the adjacent set
        adjacent.difference_update(positions)

        return adjacent

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
        turn_msg2: str = 'поставить камень. Нажмите З, чтобы пропустить ход'
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
        esc_text: pygame.Surface = self.font.render("ESC", True, (
            BLACK.r, BLACK.g, BLACK.b))
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

        pygame.time.wait(100)

    def undo_move(self):
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
        if self.board_that_could_redo is not None and self.redo_flag:
            self.board = self.board_that_could_redo
            self.move_log = self.move_log_redo
            if not self.black_turn:
                self.black_turn = True
            else:
                self.black_turn = False
            self.draw()


class Draw:
    @staticmethod
    def draw_esc_button(esc_button_hovered, previous_screen, font,
                        screen) -> None:
        esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
        button_color: Rgb = BUTTON_HOVER_COLOR if esc_button_hovered else BUTTON_COLOR
        assert previous_screen is not None  # For type checker
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

    def draw(self, board, size, board_offset_x, board_offset_y, screen,
             black_stone_image, white_stone_image, prisoners,
             font, black_turn, move_log, esc_button_hovered, previous_screen,
             start_points, end_points) -> None:
        self.clear_screen(previous_screen, screen, start_points, end_points,
                          board_offset_x, board_offset_y, size)
        self.draw_stone_image(board, size, board_offset_x, board_offset_y,
                              screen, white_stone_image, board_value=1)
        self.draw_stone_image(board, size, board_offset_x, board_offset_y,
                              screen,
                              black_stone_image, board_value=2)

        score_msg: str = (
            f"Захвачено белых камней: {prisoners['white']} "
            f"Захвачено чёрных камней: {prisoners['black']}"
        )
        txt: pygame.Surface = font.render(score_msg, True,
                                          (BLACK.r, BLACK.g, BLACK.b))
        screen.blit(txt, (
            board_offset_x + SCORE_POS[0], board_offset_y + SCORE_POS[1]))

        turn_msg1: str = (
            f"{'Белые' if not black_turn else 'Чёрные'} ходят. "
            "Нажмите на левую кнопку мыши, чтобы"
        )
        turn_msg2: str = 'поставить камень. Нажмите З, чтобы пропустить ход'
        txt1: pygame.Surface = font.render(turn_msg1, True,
                                           (BLACK.r, BLACK.g, BLACK.b))
        txt2: pygame.Surface = font.render(turn_msg2, True,
                                           (BLACK.r, BLACK.g, BLACK.b))
        screen.blit(txt1, (board_offset_x + BOARD_BORDER, board_offset_y + 10))
        screen.blit(txt2, (board_offset_x + BOARD_BORDER, board_offset_y + 50))

        log_text: str = "Лог ходов: " + ", ".join(move_log[:4])
        log_rendered: pygame.Surface = font.render(log_text, True,
                                                   (BLACK.r, BLACK.g, BLACK.b))
        screen.blit(
            log_rendered,
            (board_offset_x + BOARD_BORDER,
             board_offset_y + BOARD_WIDTH - BOARD_BORDER + 60)
        )

        esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
        if esc_button_hovered:
            pygame.draw.rect(screen, (100, 100, 100), esc_button_rect)
        else:
            pygame.draw.rect(screen, (200, 200, 200), esc_button_rect)

        pygame.draw.line(screen, (BLACK.r, BLACK.g, BLACK.b), (15, 15),
                         (55, 55), 3)
        pygame.draw.line(screen, (BLACK.r, BLACK.g, BLACK.b), (15, 55),
                         (55, 15), 3)
        esc_text: pygame.Surface = font.render("ESC", True,
                                               (BLACK.r, BLACK.g, BLACK.b))
        screen.blit(esc_text, (6, 60))

        self.draw_esc_button(esc_button_hovered, previous_screen, font, screen)
        pygame.display.flip()

    @staticmethod
    def clear_screen(previous_screen, screen, start_points, end_points,
                     board_offset_x, board_offset_y, size) -> None:
        assert previous_screen is not None
        previous_screen.blit(screen, (0, 0))
        screen.fill((BOARD_BROWN.r, BOARD_BROWN.g, BOARD_BROWN.b))
        for start_point, end_point in zip(start_points, end_points):
            start_point_screen: Point = Point(
                start_point.x + board_offset_x,
                start_point.y + board_offset_y,
            )
            end_point_screen: Point = Point(
                end_point.x + board_offset_x,
                end_point.y + board_offset_y,
            )
            pygame.draw.line(screen, (BLACK.r, BLACK.g, BLACK.b),
                             (start_point_screen.x, start_point_screen.y),
                             (end_point_screen.x, end_point_screen.y))

        guide_dots: list[int] = [3, size // 2, size - 4]
        for col, row in itertools.product(guide_dots, guide_dots):
            point: Point = Point(0, 0)
            point = point.colrow_to_point(col, row, size)
            res_point = Point(point.x + board_offset_x,
                              point.y + board_offset_y)
            gfxdraw.aacircle(screen, res_point.x, res_point.y, DOT_RADIUS,
                             (BLACK.r, BLACK.g, BLACK.b))
            gfxdraw.filled_circle(screen, res_point.x, res_point.y, DOT_RADIUS,
                                  (BLACK.r, BLACK.g, BLACK.b))
