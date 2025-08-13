# dungeon.py
import pygame
from constants import *

DIRS = {"up": (0,-1), "down": (0,1), "left": (-1,0), "right": (1,0)}

class Room:
    def __init__(self, gx: int, gy: int):
        self.gx = gx
        self.gy = gy
        self.visited = False
        # Boxed room: walls around, floor inside
        self.tiles = [[TILE_WALL if x==0 or y==0 or x==ROOM_TILES_W-1 or y==ROOM_TILES_H-1 else TILE_FLOOR
                       for x in range(ROOM_TILES_W)] for y in range(ROOM_TILES_H)]
        self.doors = set()  # {"up","down","left","right"}

    # ---- Door helpers ----
    def add_door(self, side: str):
        self.doors.add(side)
        if side == "up":      x, y = ROOM_TILES_W//2, 0
        elif side == "down":  x, y = ROOM_TILES_W//2, ROOM_TILES_H-1
        elif side == "left":  x, y = 0, ROOM_TILES_H//2
        elif side == "right": x, y = ROOM_TILES_W-1, ROOM_TILES_H//2
        self.tiles[y][x] = TILE_DOOR

    def door_transition_rects(self):
        """Small rectangles at each doorway you can collide with to change rooms."""
        rects = []
        if "up" in self.doors:
            rects.append((pygame.Rect((ROOM_TILES_W//2)*TILE_SIZE, 0, TILE_SIZE, TILE_SIZE//2), "up"))
        if "down" in self.doors:
            rects.append((pygame.Rect((ROOM_TILES_W//2)*TILE_SIZE, ROOM_PIX_H - TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2), "down"))
        if "left" in self.doors:
            rects.append((pygame.Rect(0, (ROOM_TILES_H//2)*TILE_SIZE, TILE_SIZE//2, TILE_SIZE), "left"))
        if "right" in self.doors:
            rects.append((pygame.Rect(ROOM_PIX_W - TILE_SIZE//2, (ROOM_TILES_H//2)*TILE_SIZE, TILE_SIZE//2, TILE_SIZE), "right"))
        return rects

    # ---- Collision vs walls ----
    def rect_collides(self, rect: pygame.Rect) -> bool:
        left   = max(0, rect.left // TILE_SIZE)
        right  = min(ROOM_TILES_W-1, (rect.right-1) // TILE_SIZE)
        top    = max(0, rect.top // TILE_SIZE)
        bottom = min(ROOM_TILES_H-1, (rect.bottom-1) // TILE_SIZE)
        for ty in range(top, bottom+1):
            for tx in range(left, right+1):
                if self.tiles[ty][tx] == TILE_WALL:
                    tr = pygame.Rect(tx*TILE_SIZE, ty*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if rect.colliderect(tr):
                        return True
        return False

    # ---- Drawing (fallback rectangles; swap to images later if you want) ----
    def draw(self, surf: pygame.Surface):
        surf.fill(COLOR_FLOOR)
        for y in range(ROOM_TILES_H):
            for x in range(ROOM_TILES_W):
                t = self.tiles[y][x]
                if t == TILE_WALL:
                    pygame.draw.rect(surf, COLOR_WALL, (x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE))
                elif t == TILE_DOOR:
                    pygame.draw.rect(surf, COLOR_DOOR, (x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE))

class Dungeon:
    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        self.grid = [[Room(x, y) for x in range(cols)] for y in range(rows)]
        # Open doors between neighbors
        for y in range(rows):
            for x in range(cols):
                r = self.grid[y][x]
                if y > 0:        r.add_door("up")
                if y < rows-1:   r.add_door("down")
                if x > 0:        r.add_door("left")
                if x < cols-1:   r.add_door("right")
        self.start_room = self.grid[rows//2][cols//2]

    def neighbor(self, room: Room, side: str) -> Room | None:
        dx, dy = DIRS[side]
        nx, ny = room.gx + dx, room.gy + dy
        if 0 <= nx < self.cols and 0 <= ny < self.rows:
            return self.grid[ny][nx]
        return None

    def find_door_transition(self, room: Room, player_rect: pygame.Rect) -> str | None:
        for rect, side in room.door_transition_rects():
            if player_rect.colliderect(rect):
                return side
        return None
