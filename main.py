# main.py
import sys, pygame
from constants import *
from game import Game

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Tiny Zelda-like Dungeon")
    clock = pygame.time.Clock()

    game = Game(screen)
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        try:
            game.update(dt)
        except SystemExit:
            running = False
            break
        game.render()
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
