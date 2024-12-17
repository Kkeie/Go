import pygame as pg
from gamemenu import GameMenu
from game import Game


def start_game() -> None:
    while True:
        menu = GameMenu()

        selected_size, selected_mode = menu.show_main_menu()
        game = Game(size=selected_size, mode=selected_mode)
        game.init_pygame()
        game.draw()

        while True:
            if game.update():  # Проверка возврата в меню
                break  # Выход из игрового цикла для возврата в меню

            pg.time.wait(100)


if __name__ == "__main__":
    start_game()
