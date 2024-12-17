# renderer.py

import pygame
from pygame import gfxdraw
import itertools
import numpy as np
from point import Point
from settings import *
from main_logic import game_logic
class Renderer:
    def __init__(self, size: int, screen: pygame.Surface, board_offset_x: int, board_offset_y: int, font: pygame.font.Font):
        self._size = size
        self._screen = screen
        self._board_offset_x = board_offset_x
        self._board_offset_y = board_offset_y
        self._font = font
        self._game_logic = game_logic(self._size)

        self._stone_scale_factor = board_scale[self._size]

        self._black_stone_image: pygame.Surface = pygame.image.load("black_stone.png")
        self._white_stone_image: pygame.Surface = pygame.image.load("white_stone.png")

        new_size: int = int(STONE_RADIUS * 2 * self._stone_scale_factor)
        self._black_stone_image = pygame.transform.scale(self._black_stone_image, (new_size, new_size))
        self._white_stone_image = pygame.transform.scale(self._white_stone_image, (new_size, new_size))

        self._previous_screen = pygame.Surface(self._screen.get_size())

    def _clear_screen(self, start_points: list[Point], end_points: list[Point]) -> None:
        self._previous_screen.blit(self._screen, (0, 0))
        self._screen.fill((BOARD_BROWN.r, BOARD_BROWN.g, BOARD_BROWN.b))
        for start_point, end_point in zip(start_points, end_points):
            start_point_screen: Point = Point(
                start_point.x + self._board_offset_x,
                start_point.y + self._board_offset_y,
            )
            end_point_screen: Point = Point(
                end_point.x + self._board_offset_x,
                end_point.y + self._board_offset_y,
            )
            pygame.draw.line(self._screen, (BLACK.r, BLACK.g, BLACK.b),
                             (start_point_screen.x, start_point_screen.y),
                             (end_point_screen.x, end_point_screen.y), width=2)

        guide_dots: list[int] = [3, self._size // 2, self._size - 4]
        for col, row in itertools.product(guide_dots, guide_dots):
            point: Point = Point(0, 0)
            point = self._game_logic.colrow_to_point(col, row)
            res_point = Point(point.x + self._board_offset_x,
                              point.y + self._board_offset_y)
            gfxdraw.aacircle(self._screen, res_point.x, res_point.y, DOT_RADIUS,
                             (BLACK.r, BLACK.g, BLACK.b))
            gfxdraw.filled_circle(self._screen, res_point.x, res_point.y,
                                  DOT_RADIUS, (BLACK.r, BLACK.g, BLACK.b))

    def draw(self, board: np.ndarray, prisoners: dict[str, int], black_turn: bool, move_log: list[str], esc_button_hovered: bool,
             start_points: list[Point], end_points: list[Point], mode: str):
        self._clear_screen(start_points, end_points)
        self._draw_stone_image(board, self._white_stone_image, 1)
        self._draw_stone_image(board, self._black_stone_image, 2)

        score_msg: str = (
            f"Захвачено белых камней: {prisoners['white']} "
            f"Захвачено чёрных камней: {prisoners['black']}"
        )
        txt: pygame.Surface = self._font.render(score_msg, True,
                                                (BLACK.r, BLACK.g, BLACK.b))
        self._screen.blit(txt, (self._board_offset_x + SCORE_POS[0],
                                self._board_offset_y + SCORE_POS[1]))

        turn_msg1: str = (
            f"{'Белые' if not black_turn else 'Чёрные'} ходят. "
            "Нажмите на левую кнопку мыши, чтобы"
        )
        turn_msg2: str = 'поставить камень. Нажмите ESC, чтобы пропустить ход'
        txt1: pygame.Surface = self._font.render(turn_msg1, True,
                                                 (BLACK.r, BLACK.g, BLACK.b))
        txt2: pygame.Surface = self._font.render(turn_msg2, True,
                                                 (BLACK.r, BLACK.g, BLACK.b))
        self._screen.blit(txt1, (
            self._board_offset_x + BOARD_BORDER, self._board_offset_y + 10))
        self._screen.blit(txt2, (
            self._board_offset_x + BOARD_BORDER, self._board_offset_y + 50))

        log_text: str = "Лог ходов: " + ", ".join(move_log[:4])
        log_rendered: pygame.Surface = self._font.render(log_text, True, (
            BLACK.r, BLACK.g, BLACK.b))
        self._screen.blit(
            log_rendered,
            (self._board_offset_x + BOARD_BORDER,
             self._board_offset_y + BOARD_WIDTH - BOARD_BORDER + 60)
        )

        esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
        if esc_button_hovered:
            pygame.draw.rect(self._screen, (100, 100, 100), esc_button_rect)
        else:
            pygame.draw.rect(self._screen, (200, 200, 200), esc_button_rect)

        pygame.draw.line(self._screen, (BLACK.r, BLACK.g, BLACK.b), (15, 15),(55, 55), 3)
        pygame.draw.line(self._screen, (BLACK.r, BLACK.g, BLACK.b), (15, 55),
                         (55, 15), 3)
        esc_text: pygame.Surface = self._font.render("ESC", True,
                                                     (BLACK.r, BLACK.g, BLACK.b))
        self._screen.blit(esc_text, (6, 60))

        self._draw_esc_button(esc_button_hovered)
        if mode != GameModes.ONLINE:
            self._draw_buttons()
        pygame.display.flip()

    def _draw_stone_image(self, board: np.ndarray, stone_image: pygame.Surface, board_value: int) -> None:
        for col, row in zip(*np.where(board == board_value)):
            point = Point(0, 0)
            point = self._game_logic.colrow_to_point(col, row)
            point = Point(point.x + self._board_offset_x, point.y + self._board_offset_y)
            self._screen.blit(stone_image,
                              (point.x - stone_image.get_width() // 2,
                              point.y - stone_image.get_height() // 2))

    def _draw_buttons(self) -> None:
        screen_height = self._screen.get_height()

        # Undo Button
        undo_button_rect = pygame.Rect(10, screen_height - 120, 100, 50)
        pygame.draw.rect(self._screen, (BUTTON_COLOR.r, BUTTON_COLOR.g, BUTTON_COLOR.b), undo_button_rect)
        undo_text = self._font.render("Undo", True, (BLACK.r, BLACK.g, BLACK.b))
        self._screen.blit(undo_text, (undo_button_rect.x + 20, undo_button_rect.y + 10))

        # Redo Button
        redo_button_rect = pygame.Rect(10, screen_height - 60, 100, 50)
        pygame.draw.rect(self._screen, (BUTTON_COLOR.r, BUTTON_COLOR.g, BUTTON_COLOR.b), redo_button_rect)
        redo_text = self._font.render("Redo", True, (BLACK.r, BLACK.g, BLACK.b))
        self._screen.blit(redo_text, (redo_button_rect.x + 20, redo_button_rect.y + 10))

    def _draw_esc_button(self, esc_button_hovered: bool) -> None:
        esc_button_rect = pygame.Rect(10, 10, 50, 50)
        button_color = BUTTON_HOVER_COLOR if esc_button_hovered else BUTTON_COLOR

        pygame.draw.rect(self._previous_screen, (button_color.r, button_color.g, button_color.b), esc_button_rect)
        pygame.draw.line(self._previous_screen, (BLACK.r, BLACK.g, BLACK.b), (15, 15), (55, 55), 3)
        pygame.draw.line(self._previous_screen, (BLACK.r, BLACK.g, BLACK.b), (15, 55), (55, 15), 3)
        esc_text = self._font.render("ESC", True, (BLACK.r, BLACK.g, BLACK.b))
        self._previous_screen.blit(esc_text, (6, 60))

        self._screen.blit(self._previous_screen, esc_button_rect, esc_button_rect)
        pygame.display.update(esc_button_rect)
