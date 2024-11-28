import pygame as pg
from Game_menu import Game_menu
import Game


def start_game() -> None:
    while True:
        game = Game.Game(size=8, mode="Игрок против Игрока")  # Временные значения
        game.init_pygame()
        game_menu = Game_menu()

        selected_size, selected_mode = Game_menu.show_main_menu(game_menu)
        game = Game.Game(size=selected_size, mode=selected_mode)
        game.init_pygame()
        game.clear_screen()
        game.draw()

        while True:
            if game.update():  # Проверка возврата в меню
                break  # Выход из игрового цикла для возврата в меню

            pg.time.wait(100)


if __name__ == "__main__":
    start_game()
