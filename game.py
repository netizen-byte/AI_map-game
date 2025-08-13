# game.py
import pygame
from constants import *
from camera import Camera
from dungeon import Dungeon
from player import Player

TRANSITION_COOLDOWN = 0.25  # seconds

class SolidTile(pygame.sprite.Sprite):
    """Invisible obstacle that gives us a .hitbox for enemy pathing/collision."""
    def __init__(self, group, rect):
        super().__init__(group)
        self.image = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        self.rect = rect.copy()
        self.hitbox = self.rect.copy()

class Game:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.camera = Camera()
        self.dungeon = Dungeon(DUNGEON_COLS, DUNGEON_ROWS)
        self.current_room = self.dungeon.start_room
        self.current_room.visited = True

        # player
        px = ROOM_PIX_W//2 - 10
        py = ROOM_PIX_H//2 - 10
        self.player = Player(px, py)
        self.camera.snap_to(0, 0)

        # sprite groups
        self.visible_sprites = pygame.sprite.LayeredUpdates()
        self.obstacle_sprites = pygame.sprite.Group()

        # build obstacles from current room walls
        self._rebuild_obstacles_from_room(self.current_room)

        self.door_cooldown = 0.0

        # fog-of-war surface reused each frame
        self.fog_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    # ---------- helpers ----------
    def _rebuild_obstacles_from_room(self, room):
        self.obstacle_sprites.empty()
        for ty in range(ROOM_TILES_H):
            for tx in range(ROOM_TILES_W):
                if room.tiles[ty][tx] == TILE_WALL:
                    r = pygame.Rect(tx*TILE_SIZE, ty*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    SolidTile(self.obstacle_sprites, r)

    def _render_health_bar(self):
        bar_w = 100
        bar_h = 10
        x, y = 10, 10
        pygame.draw.rect(self.screen, (60, 0, 0), (x, y, bar_w, bar_h))
        ratio = self.player.hp / PLAYER_MAX_HP
        pygame.draw.rect(self.screen, (220, 0, 0), (x, y, int(bar_w * ratio), bar_h))
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, bar_w, bar_h), 1)

    # ---------- main loop ----------
    def update(self, dt: float):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                raise SystemExit
            self.player.handle_event(e)

        # player movement
        self.player.update(dt, self.current_room)

        # door cooldown
        if self.door_cooldown > 0:
            self.door_cooldown -= dt

        # room transition
        if self.door_cooldown <= 0:
            side = self.dungeon.find_door_transition(self.current_room, self.player.rect)
            if side:
                nxt = self.dungeon.neighbor(self.current_room, side)
                if nxt:
                    # place just inside new room
                    if side == "up":
                        self.player.rect.centerx = ROOM_PIX_W//2
                        self.player.rect.centery = ROOM_PIX_H - int(TILE_SIZE*1.5)
                    elif side == "down":
                        self.player.rect.centerx = ROOM_PIX_W//2
                        self.player.rect.centery = int(TILE_SIZE*1.5)
                    elif side == "left":
                        self.player.rect.centerx = ROOM_PIX_W - int(TILE_SIZE*1.5)
                        self.player.rect.centery = ROOM_PIX_H//2
                    elif side == "right":
                        self.player.rect.centerx = int(TILE_SIZE*1.5)
                        self.player.rect.centery = ROOM_PIX_H//2

                    self.current_room = nxt
                    self.current_room.visited = True
                    self._rebuild_obstacles_from_room(self.current_room)
                    if self.current_room.trap and not self.current_room.trap_triggered:
                        self.player.take_damage(TRAP_DAMAGE)
                        self.current_room.trap_triggered = True
                    self.door_cooldown = TRANSITION_COOLDOWN

        # update sprites (movement/animation)
        self.visible_sprites.update()

    def render(self):
        self.current_room.draw(self.screen)
        self.visible_sprites.draw(self.screen)
        self.player.render(self.screen)
        self._render_health_bar()

        # Fog of war: dark overlay with a transparent circle around the player
        self.fog_surface.fill((0, 0, 0, FOG_ALPHA))
        pygame.draw.circle(self.fog_surface, (0, 0, 0, 0), self.player.rect.center, FOG_RADIUS)
        self.screen.blit(self.fog_surface, (0, 0))
