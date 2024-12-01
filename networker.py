# network_manager.py

import socket
import pygame
import sys
import select
import traceback
from typing import Optional, Tuple
from settings import *
from point import Point

class NetworkManager:
    def __init__(self, mode: str, font: pygame.font.Font, screen: pygame.Surface):
        self.mode = mode
        self.font = font
        self.screen = screen

        self.network_role = None  # 'host' или 'client'
        self.player_color = None  # 'black' или 'white'
        self.opponent_color = None
        self.conn: Optional[socket.socket] = None
        self.server_socket: Optional[socket.socket] = None
        self.black_turn = True  # Черные ходят первыми

    def setup_network(self):
        choice_made = False

        while not choice_made:
            self.screen.fill((WHITE.r, WHITE.g, WHITE.b))
            # Создаем кнопки "Создать игру" и "Присоединиться к игре"
            host_button_rect = pygame.Rect(
                self.screen.get_width() // 2 - 150, self.screen.get_height() // 2 - 60, 300, 55)
            join_button_rect = pygame.Rect(
                self.screen.get_width() // 2 - 190, self.screen.get_height() // 2 + 10, 380, 55)

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

    def send_move(self, move_str: str) -> None:
        if self.conn:
            self.conn.send(move_str.encode())

    def receive_move(self) -> Optional[Point]:
        if self.conn:
            try:
                ready_to_read, _, _ = select.select([self.conn], [], [], 0)
                if self.conn in ready_to_read:
                    data = self.conn.recv(1024)
                    if data:
                        move = data.decode().strip()
                        col, row = move.split(',')
                        return Point(int(col), int(row))
            except Exception:
                traceback.print_exc()
                pygame.quit()
                sys.exit()
        return None
