import random
import sys
import collections
import pygame
from pygame import gfxdraw
import itertools
import numpy as np
from Settings import *  # type: ignore
from MainLogic import Game_logic  # type: ignore
from typing import List, Tuple, Optional, Dict


class Game:
    def __init__(self, size: int, mode: str):
        self.logic: Game_logic = Game_logic()
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

        self.board[col, row] = 1 if not self.black_turn else 2
        move_description = f"{'Белые' if not self.black_turn else 'Чёрные'}: {col + 1},{row + 1}"
        self.move_log.insert(0, move_description)
        if len(self.move_log) > 4:
            self.move_log.pop()

        self._handle_captures(col, row)

        if self.mode == "Лёгкий":
            if not self.black_turn:
                self.black_turn = True
                self.draw()
                pygame.time.wait(1000)
                self._computer_move()
            else:
                self.black_turn = False
        else:
            self.black_turn = not self.black_turn

        self.draw()

    def _handle_captures(self, col: int, row: int) -> None:
        self_color = "white" if not self.black_turn else "black"
        other_color = "black" if not self.black_turn else "white"
        capture_happened = False

        for group in list(self.logic.get_stone_groups(self.board, other_color)):
            if self.logic.stone_group_has_no_liberties(self.board, group):
                capture_happened = True
                for i, j in group:
                    self.board[i, j] = 0
                self.prisoners[self_color] += len(group)

        if not capture_happened:
            group = None
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

            self.move_log.insert(0, f"Чёрные: {col}, {row}")
            self.move_log = self.move_log[:4]

            self.draw()
            self.black_turn = False



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
        turn_msg2 = 'поставить камень. Нажмите З, чтобы пропустить ход'
        txt1 = self.font.render(turn_msg1, antialias_on, BLACK)
        txt2 = self.font.render(turn_msg2, antialias_on, BLACK)
        self.screen.blit(txt1, (self.board_offset_x + BOARD_BORDER, self.board_offset_y + 10))
        self.screen.blit(txt2, (self.board_offset_x + BOARD_BORDER, self.board_offset_y + 50))

        log_text = "Лог ходов: " + ", ".join(self.move_log[:4])
        log_rendered = self.font.render(log_text, antialias_on, BLACK)
        self.screen.blit(log_rendered, (self.board_offset_x + BOARD_BORDER, self.board_offset_y + BOARD_WIDTH - BOARD_BORDER + 60))

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
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                self._pass_turn()

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

