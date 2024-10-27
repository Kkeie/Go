import g02 as go
import pygame as pg

def main():
    while True:
        game = go.Game(size=8, mode="Игрок против Игрока")  # Временные значения
        game.init_pygame()

        selected_size, selected_mode = game.show_size_mode_selection_menu()
        game = go.Game(size=selected_size, mode=selected_mode)
        game.init_pygame()
        game.clear_screen()
        game.draw()

        while True:
            if game.update():  # Проверка возврата в меню
                break  # Выход из игрового цикла для возврата в меню

            pg.time.wait(100)


if __name__ == "__main__":
    main()