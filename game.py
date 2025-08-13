# game.py
import pygame
import random
from constants import *
from camera import Camera
from dungeon import Dungeon
from player import Player
from enemy import Enemy
from settings import ENEMY_SPAWNS, ENEMY_SPAWN_CHANCE

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
        self.enemies = pygame.sprite.Group()

        # build obstacles from current room walls
        self._rebuild_obstacles_from_room(self.current_room)

        # per-room enemy storage
        self.room_enemies: dict[tuple[int,int], list[Enemy]] = {}
        self._ensure_room_enemies(self.current_room)

        self.door_cooldown = 0.0

    # ---------- callbacks used by Enemy ----------
    def damage_player(self, amount, atk_type, pos):
        # player already has take_damage(amount, source_pos)
        self.player.take_damage(amount, pos)

    def trigger_death_particles(self, pos, monster_name):
        # hook your particle system here later
        pass

    def add_exp(self, amount):
        # if you don’t track EXP yet, no-op
        pass

    # ---------- helpers ----------
    def _rebuild_obstacles_from_room(self, room):
        self.obstacle_sprites.empty()
        for ty in range(ROOM_TILES_H):
            for tx in range(ROOM_TILES_W):
                if room.tiles[ty][tx] == TILE_WALL:
                    r = pygame.Rect(tx*TILE_SIZE, ty*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    SolidTile(self.obstacle_sprites, r)

    def _ensure_room_enemies(self, room):
        key = (room.gx, room.gy)
        # Already initialized for this room? Re-attach live ones to groups and return.
        if key in self.room_enemies:
            for en in self.room_enemies[key]:
                if en.alive():
                    en.add(self.visible_sprites, self.enemies)
            return self.room_enemies[key]

        # Not initialized: build from settings-driven spawns (or empty if none)
        spawns = ENEMY_SPAWNS.get(key, [])
        created = []
        for name, loc in spawns:
            # roll chance to spawn (lower chance = fewer enemies)
            if random.random() > ENEMY_SPAWN_CHANCE:
                continue

            # convert tile→px if needed
            if isinstance(loc, tuple) and len(loc) == 3 and loc[0] == "tile":
                _, tx, ty = loc
                px = tx * TILE_SIZE + TILE_SIZE // 2
                py = ty * TILE_SIZE + TILE_SIZE // 2
            elif isinstance(loc, tuple) and len(loc) == 3 and loc[0] == "px":
                _, px, py = loc
            else:
                # fallback center
                px = ROOM_PIX_W // 2
                py = ROOM_PIX_H // 2

            created.append(
                Enemy(name, (px, py),
                    [self.visible_sprites, self.enemies],
                    self.obstacle_sprites,
                    self.damage_player, self.trigger_death_particles, self.add_exp)
            )

        self.room_enemies[key] = created
        return created

    # ---------- main loop ----------
    def update(self, dt: float):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                raise SystemExit
            self.player.handle_event(e)

        # enemies decide state based on player
        for en in list(self.enemies):
            en.enemy_update(self.player)

        # player movement (enemies only block if not i-framed)
        solids = [en.rect for en in self.enemies if en.alive()] if self.player.iframes <= 0 else []
        self.player.update(dt, self.current_room, solids)

        # player weapon hits → damage enemies
        hb = self.player.attack_hitbox()
        if hb:
            for en in list(self.enemies):
                if en.alive() and hb.colliderect(en.rect):
                    en.get_damage(self.player, 'weapon')

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
                    self._ensure_room_enemies(self.current_room)
                    self.door_cooldown = TRANSITION_COOLDOWN

        # update sprites (movement/animation)
        self.visible_sprites.update()
        for en in list(self.enemies):
            if not en.alive():
                self.enemies.remove(en)

    def render(self):
        self.current_room.draw(self.screen)
        # draw enemy sprites
        self.visible_sprites.draw(self.screen)
        # HUDs / extra overlays
        for en in self.enemies:
            en.render_extras(self.screen)
        self.player.render(self.screen)
