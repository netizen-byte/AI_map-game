import pygame
from constants import SCREEN_W, SCREEN_H
from game import Game
import ctypes
import sys

if sys.platform == "win32":
    ctypes.windll.user32.SetProcessDPIAware()

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
        # Respect explicit newlines: split into paragraphs first, then wrap each
        paragraphs = text.split("\n")
        out_lines = []
        for para in paragraphs:
            if not para.strip():
                # Preserve intentional blank lines
                out_lines.append("")
                continue
            words = para.split()
            cur = ""
            for w in words:
                test = (cur + " " + w).strip()
                if font.size(test)[0] > max_w and cur:
                    out_lines.append(cur)
                    cur = w
                else:
                    cur = test
            if cur:
                out_lines.append(cur)
        return out_lines


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
            (
                "One day, the world cracked. From the skies bled ruin, and the earth itself howled.\n"
                "Every awakened soul was dragged into the Tower of Calamity—twelve floors etched in blood and myth.\n"
                "Only those who slay the guardians within can shield the dying world outside.\n\n"
                "Among them was a student no prophecy ever mentioned: an international computer engineering kid from KMITL.\n"
                "The Tower spat out his title—Hunter, Rank F. F for failure, F for forgotten.\n"
                "It matched his grades perfectly, but this time he swore the story wouldn’t end the same.\n\n"
                "The halls bend like code gone mad; doors lead to rooms that shift with every breath.\n"
                "Some are safe, most are not. The only way forward is through.\n"
                "If the guardian of the final chamber falls, the Tower sleeps again.\n"
                "If he falls, the Tower devours his name, as it has devoured countless before.\n\n"
                "They call it the Chronicle of Ashes, but he will carve another ending.\n"
                "This world won’t collapse like his GPA. This time, the grade is survival."
            )
        ]


    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.page < len(self.pages) - 1:
                    self.page += 1
                else:
                    self.done = True
                    self.next_scene = TutorialScene(self.screen)
            elif ev.key == pygame.K_ESCAPE:
                self.done = True
                self.next_scene = TutorialScene(self.screen)

    def draw(self):
        self.screen.fill((16, 18, 24))
        head = self.mid.render("Prologue", True, (255, 230, 150))
        self._center(head, 80)

        # Center wrapped lines
        max_w = int(SCREEN_W * 0.78)  # limit wrap width to readable column
        lines = self._wrap_lines(self.pages[self.page], self.small, max_w)
        y = 170
        for line in lines:
            if line == "":
                y += self.small.get_height()  # blank line spacing
                continue
            surf = self.small.render(line, True, (230, 232, 240))
            x = SCREEN_W // 2 - surf.get_width() // 2
            self.screen.blit(surf, (x, y))
            y += surf.get_height() + 6

        foot = self.small.render("Enter to continue • Esc to skip", True, (190, 195, 210))
        self._center(foot, SCREEN_H - 60)


class TutorialScene(BaseScene):
    def __init__(self, screen):
        super().__init__(screen)
        # Animated player demo setup
        from player import Player
        self._demo_center = (SCREEN_W // 2, 420)
        self._demo_player = Player(self._demo_center)
        self._demo_cycle = ["down", "left", "up", "right"]
        self._demo_index = 0
        self._demo_timer = 0.0
        self._demo_interval = 0.6
        self._demo_walk_timer = 0.0
        self._demo_walk_step = 0.14

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.done = True
            self.next_scene = "GAMEPLAY"

    def update(self, dt: float):
        # Animate facing direction
        self._demo_timer += dt
        if self._demo_timer >= self._demo_interval:
            self._demo_timer -= self._demo_interval
            self._demo_index = (self._demo_index + 1) % len(self._demo_cycle)
            new_face = self._demo_cycle[self._demo_index]
            state = f"walk_{new_face}" if f"walk_{new_face}" in self._demo_player.anim else f"idle_{new_face}"
            self._demo_player.state = state
            self._demo_player.facing = new_face
            self._demo_player.frame = 0
            self._demo_player.timer = 0.0
        # Animate walk frames
        self._demo_walk_timer += dt
        if self._demo_walk_timer >= self._demo_walk_step:
            self._demo_walk_timer -= self._demo_walk_step
            frames = self._demo_player.anim.get(self._demo_player.state, [self._demo_player.image])
            if len(frames) > 1:
                self._demo_player.frame = (self._demo_player.frame + 1) % len(frames)
                self._demo_player.image = frames[self._demo_player.frame]

    def draw(self):
        self.screen.fill((18, 22, 28))
        head = self.mid.render("How to Play", True, (255, 240, 150))
        self._center(head, 80)

        lines = [
            "Move: WASD or Arrow Keys",
            "Attack: Space (when weapon ready)",
            "Interact / Confirm at doors: Y",
            "Cancel a choice: N",
            "Goal: Reach the final room and defeat the boss",
            "Reset: R",
            "UI: Click the buttons near the top-left to toggle Map and UCS path panels",
        ]
        y = 150
        for t in lines:
            surf = self.small.render("• " + t, True, (230, 235, 245))
            self.screen.blit(surf, (80, y))
            y += 32

        # Animated player demo panel (centered below instructions)
        panel_y = y + 20
        panel_h = 120
        panel_rect = pygame.Rect(SCREEN_W//2 - 60, panel_y, 120, panel_h)
        # Use same background color, no outline
        pygame.draw.rect(self.screen, (18, 22, 28), panel_rect, border_radius=10)
        # Direction label
        dir_labels = ["Down","Left","Up","Right"]
        label = self.small.render(dir_labels[self._demo_index], True, (255, 240, 150))
        self.screen.blit(label, (panel_rect.centerx - label.get_width()//2, panel_rect.y + 8))
        # Draw player sprite
        img = self._demo_player.image
        self.screen.blit(img, (panel_rect.centerx - img.get_width()//2, panel_rect.centery - img.get_height()//2 + 18))

        hint = self.small.render("Press Enter to start", True, (220, 225, 235))
        self._center(hint, SCREEN_H - 60)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    # for fullscreen
    # flags = pygame.FULLSCREEN | pygame.SCALED
    # screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
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
