import pygame
from constants import SCREEN_W, SCREEN_H
from game import Game

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Dungeon escape")

    game = Game(screen, room_json="room1.json")
    running = True
    while running:
        running = game.run_step()

    pygame.quit()

if __name__ == "__main__":
    main()
