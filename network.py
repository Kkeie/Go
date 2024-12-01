# network.py
import socket
import threading
from typing import Optional, Tuple

class Network:
    def __init__(self, is_server: bool, host: str = '', port: int = 5555):
        self.is_server = is_server
        self.host = host  # Для сервера оставляем пустым, чтобы принимать подключения на любом IP
        self.port = port
        self.conn: Optional[socket.socket] = None
        self.addr: Optional[Tuple[str, int]] = None
        self.connected = False

        if self.is_server:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.server_socket.bind((self.host, self.port))
                self.server_socket.listen(1)
                print(f"Сервер запущен, ожидаем подключения на порту {self.port}")
            except socket.error as e:
                print(f"Ошибка при запуске сервера: {e}")
                self.connected = False
        else:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def accept_connection(self):
        try:
            self.conn, self.addr = self.server_socket.accept()
            self.connected = True
            print(f"Подключен игрок с адресом {self.addr}")
        except socket.error as e:
            print(f"Ошибка при принятии подключения: {e}")

    def connect_to_server(self):
        try:
            self.client_socket.connect((self.host, self.port))
            self.conn = self.client_socket
            self.connected = True
            print(f"Подключен к серверу {self.host}:{self.port}")
        except socket.error as e:
            print(f"Не удалось подключиться к серверу: {e}")
            self.connected = False

    def send(self, data: str):
        if self.conn:
            try:
                self.conn.sendall(data.encode('utf-8'))
                print(f"Отправлено: {data}")
            except socket.error as e:
                print(f"Ошибка при отправке данных: {e}")

    def receive(self) -> str:
        if self.conn:
            try:
                data = self.conn.recv(1024).decode('utf-8')
                print(f"Получено: {data}")
                return data
            except socket.error as e:
                print(f"Ошибка при получении данных: {e}")
        return ''
