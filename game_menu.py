import pygame
from typing import Optional
from settings import *
import sys
from rgb import Rgb


class game_menu:
    def __init__(self):
        pygame.init()
        self.screen: pygame.Surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.font: pygame.font.Font = pygame.font.SysFont("Comic Sans", 50)
        self.title_font: pygame.font.Font = pygame.font.SysFont("Comic Sans", 100)
        self.selected_size_index: int = 0
        self.selected_mode_index: int = 0
        self.size_spacing: int = 40
        self.mode_spacing: int = 60
        self.BOARD_SIZES: list[int] = [8, 9, 13, 19]
        self.GAME_MODES: list[str] = ["Игрок против игрока", "Лёгкий", "Сложный", "Играть по сети"]

    def _draw_title(self) -> None:
        title_text: pygame.Surface = self.title_font.render("GO", True, (BLACK.r, BLACK.g, BLACK.b))
        title_rect: pygame.Rect = title_text.get_rect(
            center=(self.screen.get_width() // 2, self.screen.get_height() // 4))
        self.screen.blit(title_text, title_rect)

    def _draw_buttons(self) -> None:
        play_button_rect: pygame.Rect = pygame.Rect(self.screen.get_width() // 2 - 100,
                                                    self.screen.get_height() // 4 + 100, 200, 60)
        pygame.draw.rect(self.screen, (0, 255, 0), play_button_rect)
        play_button_text: pygame.Surface = self.font.render("Играть", True, (WHITE.r, WHITE.g, WHITE.b))
        play_text_rect: pygame.Rect = play_button_text.get_rect(center=play_button_rect.center)
        self.screen.blit(play_button_text, play_text_rect)

        exit_button_rect: pygame.Rect = pygame.Rect(self.screen.get_width() // 2 - 100,
                                                    self.screen.get_height() // 4 + 180, 200, 60)
        pygame.draw.rect(self.screen, (255, 0, 0), exit_button_rect)
        exit_button_text: pygame.Surface = self.font.render("Выйти", True, (WHITE.r, WHITE.g, WHITE.b))
        exit_text_rect: pygame.Rect = exit_button_text.get_rect(center=exit_button_rect.center)
        self.screen.blit(exit_button_text, exit_text_rect)

    def _draw_selecting_options(self) -> None:
        subtitle: pygame.Surface = self.font.render("Выберите размер поля и режим игры:", True,
                                                    (BLACK.r, BLACK.g, BLACK.b))
        subtitle_rect: pygame.Rect = subtitle.get_rect(
            center=(self.screen.get_width() // 2, self.screen.get_height() // 2 + 30))
        self.screen.blit(subtitle, subtitle_rect)

    def _draw_size_options(self) -> list[pygame.Rect]:
        size_title: pygame.Surface = self.font.render("Размер:", True, (BLACK.r, BLACK.g, BLACK.b))
        size_title_rect: pygame.Rect = size_title.get_rect(
            center=(self.screen.get_width() // 3, self.screen.get_height() // 2 + 90))
        self.screen.blit(size_title, size_title_rect)

        size_rects: list[pygame.Rect] = []
        for board_size in range(len(self.BOARD_SIZES)):
            color: Rgb = Rgb(0, 0, 0) if board_size == self.selected_size_index else Rgb(150, 150, 150)
            size_text: pygame.Surface = self.font.render(f"{self.BOARD_SIZES[board_size]}x{self.BOARD_SIZES[board_size]}", True,
                                                         (color.r, color.g, color.b))
            rect: pygame.Rect = size_text.get_rect(center=(
                self.screen.get_width() // 3, self.screen.get_height() // 2 + 160 + board_size * (self.size_spacing + 10)))
            size_rects.append(rect.inflate(20, 10))
            self.screen.blit(size_text, rect)
        return size_rects

    def _draw_mode_options(self) -> list[pygame.Rect]:
        mode_title: pygame.Surface = self.font.render("Режим:", True, (BLACK.r, BLACK.g, BLACK.b))
        mode_title_rect: pygame.Rect = mode_title.get_rect(
            center=(self.screen.get_width() * 2 // 3, self.screen.get_height() // 2 + 90))
        self.screen.blit(mode_title, mode_title_rect)

        mode_rects: list[pygame.Rect] = []
        for game_mode in range(len(self.GAME_MODES)):
            color: Rgb = Rgb(0, 0, 0) if game_mode == self.selected_mode_index else Rgb(150, 150, 150)
            mode_text: pygame.Surface = self.font.render(self.GAME_MODES[game_mode], True, (color.r, color.g, color.b))
            rect: pygame.Rect = mode_text.get_rect(center=(
                self.screen.get_width() * 2 // 3, self.screen.get_height() // 2 + 160 + game_mode * (self.mode_spacing + 10)))
            mode_rects.append(rect.inflate(20, 10))
            self.screen.blit(mode_text, rect)
        return mode_rects

    def _handle_events(self, size_rects: list[pygame.Rect], mode_rects: list[pygame.Rect]) -> Optional[tuple[int, str]]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()

                    for position, rect in enumerate(size_rects):
                        if rect.collidepoint(mouse_x, mouse_y):
                            self.selected_size_index = position
                    for position, rect in enumerate(mode_rects):
                        if rect.collidepoint(mouse_x, mouse_y):
                            self.selected_mode_index = position

                    play_button_rect: pygame.Rect = pygame.Rect(self.screen.get_width() // 2 - 100,
                                                                self.screen.get_height() // 4 + 100, 200, 60)
                    if play_button_rect.collidepoint(mouse_x, mouse_y):
                        return self.BOARD_SIZES[self.selected_size_index], self.GAME_MODES[self.selected_mode_index]

                    exit_button_rect: pygame.Rect = pygame.Rect(self.screen.get_width() // 2 - 100,
                                                                self.screen.get_height() // 4 + 180, 200, 60)
                    if exit_button_rect.collidepoint(mouse_x, mouse_y):
                        pygame.quit()
                        sys.exit()
        return None

    def show_main_menu(self) -> tuple[int, str]:
        while True:
            self.screen.fill((WHITE.r, WHITE.g, WHITE.b))

            self._draw_title()
            self._draw_buttons()
            self._draw_selecting_options()
            size_rects: list[pygame.Rect] = self._draw_size_options()
            mode_rects: list[pygame.Rect] = self._draw_mode_options()

            pygame.display.flip()

            result: Optional[tuple[int, str]] = self._handle_events(size_rects, mode_rects)
            if result:
                return result
