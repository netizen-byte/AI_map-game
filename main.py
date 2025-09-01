import pygame
from constants import SCREEN_W, SCREEN_H
from game import Game

class BaseScene:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.big = pygame.font.Font(None, 64)
        self.mid = pygame.font.Font(None, 36)
        self.small = pygame.font.Font(None, 24)
        self.done = False
        self.next_scene = None

    def run_step(self) -> bool:
        dt = self.clock.tick(60) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            self.handle_event(ev)
        self.update(dt)
        self.draw()
        pygame.display.flip()
        return True

    # hooks
    def handle_event(self, ev: pygame.event.Event): ...
    def update(self, dt: float): ...
    def draw(self): ...

    # helpers
    def _center(self, surf, y):
        self.screen.blit(surf, (self.screen.get_width()//2 - surf.get_width()//2, y))

    def _wrap_lines(self, text: str, font: pygame.font.Font, max_w: int):
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] > max_w and cur:
                lines.append(cur)
                cur = w
            else:
                cur = test
        if cur: lines.append(cur)
        return lines


class TitleScene(BaseScene):
    def __init__(self, screen):
        super().__init__(screen)
        self.blink = 0.0

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.done = True
                self.next_scene = StoryScene(self.screen)

    def update(self, dt):
        self.blink += dt

    def draw(self):
        self.screen.fill((14, 16, 22))
        title = self.big.render("Dungeon Escape", True, (255, 236, 140))
        self._center(title, 160)

        sub = self.mid.render("Find the way out", True, (220, 228, 240))
        self._center(sub, 230)

        hint_on = int((self.blink * 2) % 2) == 0
        if hint_on:
            hint = self.small.render("Press Enter to begin", True, (235, 235, 245))
            self._center(hint, 320)

        foot = self.small.render("Tip: window focus is required for keyboard input", True, (180,180,200))
        self._center(foot, SCREEN_H - 60)


class StoryScene(BaseScene):
    def __init__(self, screen):
        super().__init__(screen)
        self.page = 0
        self.pages = [
            "The library fell silent when the vault door cracked open. A map of twelve rooms, "
            "inked in a script older than the city, promised treasure—and something that shouldn’t wake.",

            "You took the key anyway. Now the halls shift underfoot; some doors lead forward, others back. "
            "Some rooms are safe. One is not. The only way is through.",

            "Legends say the final chamber houses a guardian. If it falls, the maze sleeps again. "
            "If you fall, the maze keeps your name."
        ]

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
                if self.page < len(self.pages) - 1:
                    self.page += 1
                else:
                    self.done = True
                    self.next_scene = TutorialScene(self.screen)
            elif ev.key in (pygame.K_LEFT, pygame.K_BACKSPACE):
                self.page = max(0, self.page - 1)
            elif ev.key == pygame.K_ESCAPE:
                self.done = True
                self.next_scene = TutorialScene(self.screen)

    def draw(self):
        self.screen.fill((16, 18, 24))
        head = self.mid.render("Prologue", True, (255, 230, 150))
        self._center(head, 80)

        margin_x = 80
        max_w = SCREEN_W - margin_x*2
        y = 170
        for line in self._wrap_lines(self.pages[self.page], self.small, max_w):
            surf = self.small.render(line, True, (230, 232, 240))
            self.screen.blit(surf, (margin_x, y))
            y += surf.get_height() + 6

        foot = self.small.render("LEFT / RIGHT to navigate • Enter to continue • Esc to skip", True, (190, 195, 210))
        self._center(foot, SCREEN_H - 60)


class TutorialScene(BaseScene):
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.done = True
            self.next_scene = "GAMEPLAY"

    def draw(self):
        self.screen.fill((18, 22, 28))
        head = self.mid.render("How to Play", True, (255, 240, 150))
        self._center(head, 80)

        lines = [
            "Move: WASD or Arrow Keys",
            "Attack: Space (when weapon ready)",
            "Interact / Confirm at doors: Enter / Y / E",
            "Cancel a choice: N / Esc / Backspace",
            "Goal: Reach the final room and defeat the boss",
            "UI: Click the buttons near the top-left to toggle Map and UCS path panels",
        ]
        y = 150
        for t in lines:
            surf = self.small.render("• " + t, True, (230, 235, 245))
            self.screen.blit(surf, (80, y))
            y += 32

        hint = self.small.render("Press Enter to start", True, (220, 225, 235))
        self._center(hint, SCREEN_H - 60)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Dungeon escape")

    scene: BaseScene = TitleScene(screen)
    while True:
        running = scene.run_step()
        if not running:
            pygame.quit()
            return
        if scene.done:
            nxt = scene.next_scene
            if nxt == "GAMEPLAY" or isinstance(nxt, str) and nxt.upper() == "GAMEPLAY":
                break
            scene = nxt

    game = Game(screen)
    running = True
    while running:
        running = game.run_step()

    pygame.quit()


if __name__ == "__main__":
    main()
