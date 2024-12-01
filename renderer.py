# renderer.py

import pygame
from pygame import gfxdraw
import itertools
import numpy as np
from typing import List, Dict
from point import Point
from settings import *

class Renderer:
    def __init__(self, size: int, screen: pygame.Surface, board_offset_x: int, board_offset_y: int, font: pygame.font.Font):
        self.size = size
        self.screen = screen
        self.board_offset_x = board_offset_x
        self.board_offset_y = board_offset_y
        self.font = font

        self.stone_scale_factor = board_scale[self.size]

        self.black_stone_image: pygame.Surface = pygame.image.load("black_stone.png")
        self.white_stone_image: pygame.Surface = pygame.image.load("white_stone.png")

        new_size: int = int(STONE_RADIUS * 2 * self.stone_scale_factor)
        self.black_stone_image = pygame.transform.scale(self.black_stone_image, (new_size, new_size))
        self.white_stone_image = pygame.transform.scale(self.white_stone_image, (new_size, new_size))

        self.previous_screen = pygame.Surface(self.screen.get_size())

    def clear_screen(self, start_points: List[Point], end_points: List[Point]) -> None:
        self.previous_screen.blit(self.screen, (0, 0))
        self.screen.fill((BOARD_BROWN.r, BOARD_BROWN.g, BOARD_BROWN.b))
        for start_point, end_point in zip(start_points, end_points):
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

        guide_dots: List[int] = [3, self.size // 2, self.size - 4]
        for col, row in itertools.product(guide_dots, guide_dots):
            point: Point = Point(0, 0)
            point = point.colrow_to_point(col, row, self.size)
            res_point = Point(point.x + self.board_offset_x,
                              point.y + self.board_offset_y)
            gfxdraw.aacircle(self.screen, res_point.x, res_point.y, DOT_RADIUS,
                             (BLACK.r, BLACK.g, BLACK.b))
            gfxdraw.filled_circle(self.screen, res_point.x, res_point.y,
                                  DOT_RADIUS, (BLACK.r, BLACK.g, BLACK.b))

    def draw(self, board: np.ndarray, prisoners: Dict[str, int], black_turn: bool, move_log: List[str], esc_button_hovered: bool, start_points: List[Point], end_points: List[Point], mode: str):
        self.clear_screen(start_points, end_points)
        self.draw_stone_image(board, self.white_stone_image, 1)
        self.draw_stone_image(board, self.black_stone_image, 2)

        score_msg: str = (
            f"Захвачено белых камней: {prisoners['white']} "
            f"Захвачено чёрных камней: {prisoners['black']}"
        )
        txt: pygame.Surface = self.font.render(score_msg, True,
                                               (BLACK.r, BLACK.g, BLACK.b))
        self.screen.blit(txt, (self.board_offset_x + SCORE_POS[0],
                               self.board_offset_y + SCORE_POS[1]))

        turn_msg1: str = (
            f"{'Белые' if not black_turn else 'Чёрные'} ходят. "
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

        log_text: str = "Лог ходов: " + ", ".join(move_log[:4])
        log_rendered: pygame.Surface = self.font.render(log_text, True, (
            BLACK.r, BLACK.g, BLACK.b))
        self.screen.blit(
            log_rendered,
            (self.board_offset_x + BOARD_BORDER,
             self.board_offset_y + BOARD_WIDTH - BOARD_BORDER + 60)
        )

        esc_button_rect: pygame.Rect = pygame.Rect(10, 10, 50, 50)
        if esc_button_hovered:
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

        self.draw_esc_button(esc_button_hovered)
        if mode != GameModes.ONLINE:
            self.draw_buttons()
        pygame.display.flip()

    def draw_stone_image(self, board: np.ndarray, stone_image: pygame.Surface, board_value: int) -> None:
        for col, row in zip(*np.where(board == board_value)):
            point = Point(0, 0)
            point = point.colrow_to_point(col, row, self.size)
            point = Point(point.x + self.board_offset_x, point.y + self.board_offset_y)
            self.screen.blit(stone_image,
                             (point.x - stone_image.get_width() // 2,
                              point.y - stone_image.get_height() // 2))

    def draw_buttons(self) -> None:
        screen_height = self.screen.get_height()

        # Undo Button
        undo_button_rect = pygame.Rect(10, screen_height - 120, 100, 50)
        pygame.draw.rect(self.screen, (BUTTON_COLOR.r, BUTTON_COLOR.g, BUTTON_COLOR.b), undo_button_rect)
        undo_text = self.font.render("Undo", True, (BLACK.r, BLACK.g, BLACK.b))
        self.screen.blit(undo_text, (undo_button_rect.x + 20, undo_button_rect.y + 10))

        # Redo Button
        redo_button_rect = pygame.Rect(10, screen_height - 60, 100, 50)
        pygame.draw.rect(self.screen, (BUTTON_COLOR.r, BUTTON_COLOR.g, BUTTON_COLOR.b), redo_button_rect)
        redo_text = self.font.render("Redo", True, (BLACK.r, BLACK.g, BLACK.b))
        self.screen.blit(redo_text, (redo_button_rect.x + 20, redo_button_rect.y + 10))

    def draw_esc_button(self, esc_button_hovered: bool) -> None:
        esc_button_rect = pygame.Rect(10, 10, 50, 50)
        button_color = BUTTON_HOVER_COLOR if esc_button_hovered else BUTTON_COLOR

        pygame.draw.rect(self.previous_screen, (button_color.r, button_color.g, button_color.b), esc_button_rect)
        pygame.draw.line(self.previous_screen, (BLACK.r, BLACK.g, BLACK.b), (15, 15), (55, 55), 3)
        pygame.draw.line(self.previous_screen, (BLACK.r, BLACK.g, BLACK.b), (15, 55), (55, 15), 3)
        esc_text = self.font.render("ESC", True, (BLACK.r, BLACK.g, BLACK.b))
        self.previous_screen.blit(esc_text, (6, 60))

        self.screen.blit(self.previous_screen, esc_button_rect, esc_button_rect)
        pygame.display.update(esc_button_rect)
