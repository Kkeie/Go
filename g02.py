import pygame
import numpy as np
import itertools
import sys
import networkx as nx
import collections
from pygame import gfxdraw
import random

BOARD_BROWN = (186, 138, 69)
BOARD_WIDTH = 1000
BOARD_BORDER = 120
STONE_RADIUS = 35
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SCORE_POS = (BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER + 30)
DOT_RADIUS = 4
BUTTON_COLOR = (200, 200, 200)
BUTTON_HOVER_COLOR = (100, 100, 100)

BOARD_SIZES = [8, 9, 13, 19]
GAME_MODES = ["Игрок против Игрока", "Игрок против Компьютера"]


def make_grid(size):
    start_points, end_points = [], []
    xs = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
    ys = np.full(size, BOARD_BORDER)
    start_points += list(zip(xs, ys))
    xs = np.full(size, BOARD_BORDER)
    ys = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
    start_points += list(zip(xs, ys))
    xs = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
    ys = np.full(size, BOARD_WIDTH - BOARD_BORDER)
    end_points += list(zip(xs, ys))
    xs = np.full(size, BOARD_WIDTH - BOARD_BORDER)
    ys = np.linspace(BOARD_BORDER, BOARD_WIDTH - BOARD_BORDER, size)
    end_points += list(zip(xs, ys))
    return start_points, end_points


def xy_to_colrow(x, y, size):
    inc = (BOARD_WIDTH - 2 * BOARD_BORDER) / (size - 1)
    x_dist = x - BOARD_BORDER
    y_dist = y - BOARD_BORDER
    col = int(round(x_dist / inc))
    row = int(round(y_dist / inc))
    return col, row


def colrow_to_xy(col, row, size):
    inc = (BOARD_WIDTH - 2 * BOARD_BORDER) / (size - 1)
    x = int(BOARD_BORDER + col * inc)
    y = int(BOARD_BORDER + row * inc)
    return x, y


def has_no_liberties(board, group):
    for x, y in group:
        if x > 0 and board[x - 1, y] == 0:
            return False
        if y > 0 and board[x, y - 1] == 0:
            return False
        if x < board.shape[0] - 1 and board[x + 1, y] == 0:
            return False
        if y < board.shape[0] - 1 and board[x, y + 1] == 0:
            return False
    return True


def get_stone_groups(board, color):
    size = board.shape[0]
    color_code = 1 if color == "white" else 2
    xs, ys = np.where(board == color_code)
    graph = nx.grid_graph(dim=[size, size])
    stones = set(zip(xs, ys))
    all_spaces = set(itertools.product(range(size), range(size)))
    stones_to_remove = all_spaces - stones
    graph.remove_nodes_from(stones_to_remove)
    return nx.connected_components(graph)


def is_valid_move(col, row, board):
    if col < 0 or col >= board.shape[0]:
        return False
    if row < 0 or row >= board.shape[0]:
        return False
    return board[col, row] == 0


class Game:
    def __init__(self, size, mode):
        self.board = np.zeros((size, size))
        self.size = size
        self.black_turn = False
        self.prisoners = collections.defaultdict(int)
        self.start_points, self.end_points = make_grid(self.size)
        self.mode = mode
        self.stone_scale_factor = self.calculate_scale_factor()
        self.move_log = []
        self.esc_button_hovered = False
        self.previous_screen = None

    def calculate_scale_factor(self):
        if self.size == 8:
            return 1.0
        elif self.size == 9:
            return 0.9
        elif self.size == 13:
            return 0.7
        elif self.size == 19:
            return 0.5
        return 1.0

    def init_pygame(self):
        pygame.init()
        screen_info = pygame.display.Info()
        screen_width, screen_height = screen_info.current_w, screen_info.current_h
        self.screen = pygame.display.set_mode((screen_width, screen_height),
                                              pygame.FULLSCREEN)
        self.font = pygame.font.SysFont("Comic Sans", 30)
        self.black_stone_image = pygame.image.load("black_stone.png")
        self.white_stone_image = pygame.image.load("white_stone.png")

        new_size = int(STONE_RADIUS * 2 * self.stone_scale_factor)
        self.black_stone_image = pygame.transform.scale(self.black_stone_image,
                                                        (new_size, new_size))
        self.white_stone_image = pygame.transform.scale(self.white_stone_image,
                                                        (new_size, new_size))

        self.board_offset_x = (screen_width - BOARD_WIDTH) // 2
        self.board_offset_y = (screen_height - BOARD_WIDTH) // 2

        self.previous_screen = pygame.Surface(self.screen.get_size())

    def clear_screen(self):
        self.previous_screen.blit(self.screen, (0, 0))  # сохраняем предыдущий кадр
        self.screen.fill(BOARD_BROWN)
        for start_point, end_point in zip(self.start_points, self.end_points):
            start_point = (start_point[0] + self.board_offset_x,
                           start_point[1] + self.board_offset_y)
            end_point = (end_point[0] + self.board_offset_x,
                         end_point[1] + self.board_offset_y)
            pygame.draw.line(self.screen, BLACK, start_point, end_point)
        guide_dots = [3, self.size // 2, self.size - 4]
        for col, row in itertools.product(guide_dots, guide_dots):
            x, y = colrow_to_xy(col, row, self.size)
            x += self.board_offset_x
            y += self.board_offset_y
            gfxdraw.aacircle(self.screen, x, y, DOT_RADIUS, BLACK)
            gfxdraw.filled_circle(self.screen, x, y, DOT_RADIUS, BLACK)

    def pass_move(self):
        self.black_turn = not self.black_turn
        self.draw()

    def handle_click(self):
        x, y = pygame.mouse.get_pos()
        # Корректируем координаты мыши с учетом отступов
        x -= self.board_offset_x
        y -= self.board_offset_y
        col, row = xy_to_colrow(x, y, self.size)
        if not is_valid_move(col, row, self.board):
            return

        self.board[col, row] = 1 if not self.black_turn else 2
        move_description = f"{'Белые' if not self.black_turn else 'Чёрные'}: {col + 1},{row + 1}"  # Ход
        self.move_log.insert(0,
                             move_description)  # Добавление хода в начало лога
        if len(self.move_log) > 4:  # Оставляем только последние 4 хода
            self.move_log.pop()

        self.handle_captures(col, row)

        if self.mode == "Игрок против Компьютера":
            if not self.black_turn:  # После хода игрока, ход компьютера
                self.black_turn = True  # Передаем ход компьютеру
                self.draw()
                pygame.time.wait(1000)  # Задержка перед ходом компьютера
                self.computer_move()
            else:  # Вернуться к игроку после хода компьютера
                self.black_turn = False
        else:
            self.black_turn = not self.black_turn  # PVP

        self.draw()

    def handle_captures(self, col, row):
        self_color = "white" if not self.black_turn else "black"
        other_color = "black" if not self.black_turn else "white"
        capture_happened = False

        # Проверка, не захвачены ли камни противника
        for group in list(get_stone_groups(self.board, other_color)):
            if has_no_liberties(self.board, group):
                capture_happened = True
                for i, j in group:
                    self.board[i, j] = 0
                self.prisoners[self_color] += len(group)

        if not capture_happened:
            group = None
            # Проверка, захватил ли недавно установленный камень свою собственную группу
            for group in get_stone_groups(self.board, self_color):
                if (col, row) in group:
                    break
            if group and has_no_liberties(self.board, group):
                self.board[col, row] = 0

    def computer_move(self):
        valid_moves = [(col, row) for col in range(self.size) for row in
                       range(self.size) if
                       is_valid_move(col, row, self.board)]
        if valid_moves:
            col, row = random.choice(
                valid_moves)  # Случайный валидный ход для компьютера
            self.board[col, row] = 2
            self.handle_captures(col, row)

            self.move_log.insert(0, f"Чёрные: {col}, {row}")
            self.move_log = self.move_log[:4]

            self.draw()
            self.black_turn = False  # Возвращаем ход игроку

    def draw(self):
        self.clear_screen()
        for col, row in zip(*np.where(self.board == 1)):
            x, y = colrow_to_xy(col, row, self.size)
            x += self.board_offset_x
            y += self.board_offset_y
            self.screen.blit(self.white_stone_image, (
                x - self.white_stone_image.get_width() // 2,
                y - self.white_stone_image.get_height() // 2
            ))
        for col, row in zip(*np.where(self.board == 2)):
            x, y = colrow_to_xy(col, row, self.size)
            x += self.board_offset_x
            y += self.board_offset_y
            self.screen.blit(self.black_stone_image, (
                x - self.black_stone_image.get_width() // 2,
                y - self.black_stone_image.get_height() // 2
            ))

        # Отображение счета и сообщений о ходе
        score_msg = (
            f"Захвачено белых камней: {self.prisoners['white']} "
            f"Захвачено чёрных камней: {self.prisoners['black']}"
        )
        txt = self.font.render(score_msg, True, BLACK)
        self.screen.blit(txt, (self.board_offset_x + SCORE_POS[0],
                               self.board_offset_y + SCORE_POS[1]))

        turn_msg1 = (
            f"{'Белые' if not self.black_turn else 'Чёрные'} ходят. "
            "Нажмите на левую кнопку мыши, чтобы"
        )
        turn_msg2 = 'поставить камень. Нажмите З, чтобы пропустить ход'
        txt1 = self.font.render(turn_msg1, True, BLACK)
        txt2 = self.font.render(turn_msg2, True, BLACK)
        self.screen.blit(txt1, (
            self.board_offset_x + BOARD_BORDER, self.board_offset_y + 10))
        self.screen.blit(txt2, (
            self.board_offset_x + BOARD_BORDER, self.board_offset_y + 50))

        log_text = "Лог ходов: " + ", ".join(self.move_log[:4])
        log_rendered = self.font.render(log_text, True, BLACK)
        self.screen.blit(log_rendered, (self.board_offset_x + BOARD_BORDER,
                                        self.board_offset_y + BOARD_WIDTH - BOARD_BORDER + 60))

        # Кнопка "ESC" для возврата в главное меню
        esc_button_rect = pygame.Rect(10, 10, 50, 50)
        if self.esc_button_hovered:
            pygame.draw.rect(self.screen, (100, 100, 100),
                             esc_button_rect)  # Темнее при наведении
        else:
            pygame.draw.rect(self.screen, (200, 200, 200),
                             esc_button_rect)  # Обычный цвет

        pygame.draw.line(self.screen, BLACK, (15, 15), (55, 55), 3)
        pygame.draw.line(self.screen, BLACK, (15, 55), (55, 15), 3)
        esc_text = self.font.render("ESC", True, BLACK)
        self.screen.blit(esc_text, (6, 60))

        self.draw_esc_button()
        pygame.display.flip()

    def draw_esc_button(self):
        esc_button_rect = pygame.Rect(10, 10, 50, 50)
        button_color = BUTTON_HOVER_COLOR if self.esc_button_hovered else BUTTON_COLOR

        # Draw ESC button
        pygame.draw.rect(self.previous_screen, button_color, esc_button_rect)
        pygame.draw.line(self.previous_screen, BLACK, (15, 15), (55, 55), 3)
        pygame.draw.line(self.previous_screen, BLACK, (15, 55), (55, 15), 3)
        esc_text = self.font.render("ESC", True, BLACK)
        self.previous_screen.blit(esc_text, (6, 60))

        # обновление только esc
        self.screen.blit(self.previous_screen, esc_button_rect, esc_button_rect)
        pygame.display.update(esc_button_rect)
    def update(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Левая кнопка мыши
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    esc_button_rect = pygame.Rect(10, 10, 50, 50)
                    if esc_button_rect.collidepoint(mouse_x, mouse_y):
                        return True  # возвращение в главное
                    self.handle_click()
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:  # возвращение в главное меню
                    return True

        # обновление esc
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

    def show_size_mode_selection_menu(self):
        pygame.init()
        screen = pygame.display.set_mode((0, 0),
                                         pygame.FULLSCREEN)  # Полноэкранный режим
        font = pygame.font.SysFont("Comic Sans", 50)
        title_font = pygame.font.SysFont("Comic Sans", 100)
        selected_size_index = 0
        selected_mode_index = 0
        size_spacing = 40  # отступ между размерами поля
        mode_spacing = 60  # отсутп между режимами

        while True:
            screen.fill(WHITE)

            # Логотип GO
            title_text = title_font.render("GO", True, BLACK)
            title_rect = title_text.get_rect(
                center=(screen.get_width() // 2, screen.get_height() // 4))
            screen.blit(title_text, title_rect)

            # Кнопки "Играть" и "Выйти"
            play_button_rect = pygame.Rect(screen.get_width() // 2 - 100,
                                           screen.get_height() // 4 + 100, 200,
                                           60)
            pygame.draw.rect(screen, (0, 255, 0), play_button_rect)
            play_button_text = font.render("Играть", True, WHITE)
            play_text_rect = play_button_text.get_rect(
                center=play_button_rect.center)
            screen.blit(play_button_text, play_text_rect)

            exit_button_rect = pygame.Rect(screen.get_width() // 2 - 100,
                                           screen.get_height() // 4 + 180, 200,
                                           60)
            pygame.draw.rect(screen, (255, 0, 0), exit_button_rect)
            exit_button_text = font.render("Выйти", True, WHITE)
            exit_text_rect = exit_button_text.get_rect(
                center=exit_button_rect.center)
            screen.blit(exit_button_text, exit_text_rect)

            # Надпись "Выберите размер поля и режим игры:"
            subtitle = font.render("Выберите размер поля и режим игры:", True,
                                   BLACK)
            subtitle_rect = subtitle.get_rect(center=(
                screen.get_width() // 2, screen.get_height() // 2 + 30))
            screen.blit(subtitle, subtitle_rect)

            # Размеры поля
            size_title = font.render("Размер:", True, BLACK)
            size_title_rect = size_title.get_rect(center=(
                screen.get_width() // 3, screen.get_height() // 2 + 90))
            screen.blit(size_title, size_title_rect)

            size_rects = []
            for i in range(len(BOARD_SIZES)):
                color = BLACK if i == selected_size_index else (150, 150, 150)
                size_text = font.render(f"{BOARD_SIZES[i]}x{BOARD_SIZES[i]}",
                                        True, color)
                rect = size_text.get_rect(center=(screen.get_width() // 3,
                                                  screen.get_height() // 2 + 160 + i * (
                                                          size_spacing + 10)))
                size_rects.append(rect.inflate(20, 10))
                screen.blit(size_text, rect)

            # Режимы игры
            mode_title = font.render("Режим:", True, BLACK)
            mode_title_rect = mode_title.get_rect(center=(
                screen.get_width() * 2 // 3, screen.get_height() // 2 + 90))
            screen.blit(mode_title, mode_title_rect)

            mode_rects = []
            for i in range(len(GAME_MODES)):
                color = BLACK if i == selected_mode_index else (150, 150, 150)
                mode_text = font.render(GAME_MODES[i], True, color)
                rect = mode_text.get_rect(center=(screen.get_width() * 2 // 3,
                                                  screen.get_height() // 2 + 160 + i * (
                                                          mode_spacing + 10)))
                mode_rects.append(rect.inflate(20, 10))
                screen.blit(mode_text, rect)

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Проверяем, что это левая кнопка
                        # мыши
                        mouse_x, mouse_y = pygame.mouse.get_pos()

                        # Проверка выбора размера
                        for i, rect in enumerate(size_rects):
                            if rect.collidepoint(mouse_x, mouse_y):
                                selected_size_index = i

                        # Проверка выбора режима
                        for i, rect in enumerate(mode_rects):
                            if rect.collidepoint(mouse_x, mouse_y):
                                selected_mode_index = i

                        # Проверка нажатия кнопки "Играть"
                        if play_button_rect.collidepoint(mouse_x, mouse_y):
                            return BOARD_SIZES[selected_size_index], \
                                GAME_MODES[selected_mode_index]

                        # Проверка нажатия кнопки "Выйти"
                        if exit_button_rect.collidepoint(mouse_x, mouse_y):
                            pygame.quit()
                            sys.exit()


def main():
    while True:
        game = Game(size=8, mode="Игрок против Игрока")  # Временные значения
        game.init_pygame()

        selected_size, selected_mode = game.show_size_mode_selection_menu()
        game = Game(size=selected_size, mode=selected_mode)
        game.init_pygame()
        game.clear_screen()
        game.draw()

        while True:
            if game.update():  # Проверка возврата в меню
                break  # Выход из игрового цикла для возврата в меню

            pygame.time.wait(100)


if __name__ == "__main__":
    main()
