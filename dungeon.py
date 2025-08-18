# dungeon.py
import pygame
from constants import *
from map_loader import CSVRooms

DIRS = {"up": (0,-1), "down": (0,1), "left": (-1,0), "right": (1,0)}

class Room:
    def __init__(self, gx: int, gy: int, tiles_block):
        self.gx = gx
        self.gy = gy
        self.visited = False
        # walk[y][x] == True -> floor; False -> wall/void
        self.walk = [[tiles_block[y][x] != -1 for x in range(len(tiles_block[0]))]
                     for y in range(len(tiles_block))]
        self.h = len(self.walk)
        self.w = len(self.walk[0])
        self.doors = set()  # filled by Dungeon via CSV adjacency

    def door_transition_rects(self):
        rects = []
        cx = (self.w // 2) * TILE_SIZE
        cy = (self.h // 2) * TILE_SIZE
        if "up" in self.doors:
            rects.append((pygame.Rect(cx, 0, TILE_SIZE, TILE_SIZE//2), "up"))
        if "down" in self.doors:
            rects.append((pygame.Rect(cx, self.h*TILE_SIZE - TILE_SIZE//2, TILE_SIZE, TILE_SIZE//2), "down"))
        if "left" in self.doors:
            rects.append((pygame.Rect(0, cy, TILE_SIZE//2, TILE_SIZE), "left"))
        if "right" in self.doors:
            rects.append((pygame.Rect(self.w*TILE_SIZE - TILE_SIZE//2, cy, TILE_SIZE//2, TILE_SIZE), "right"))
        return rects

    def rect_collides(self, rect: pygame.Rect) -> bool:
        left   = max(0, rect.left // TILE_SIZE)
        right  = min(self.w-1, (rect.right-1) // TILE_SIZE)
        top    = max(0, rect.top // TILE_SIZE)
        bottom = min(self.h-1, (rect.bottom-1) // TILE_SIZE)
        for ty in range(top, bottom+1):
            for tx in range(left, right+1):
                if not self.walk[ty][tx]:
                    if rect.colliderect(pygame.Rect(tx*TILE_SIZE, ty*TILE_SIZE, TILE_SIZE, TILE_SIZE)):
                        return True
        return False

    def draw(self, surf: pygame.Surface):
        # simple colors; swap to tiles later if you want
        for y in range(self.h):
            for x in range(self.w):
                r = pygame.Rect(x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(surf, COLOR_FLOOR if self.walk[y][x] else COLOR_WALL, r)

class Dungeon:
    def __init__(self, csv_rooms: CSVRooms | None = None):
        self.csv_rooms = csv_rooms
        if csv_rooms:
            self.cols = csv_rooms.cols
            self.rows = csv_rooms.rows
            self.grid = [[Room(x, y, csv_rooms.room_block(y, x)) for x in range(self.cols)]
                         for y in range(self.rows)]
            # detect “doors” (open edges)
            for y in range(self.rows):
                for x in range(self.cols):
                    r = self.grid[y][x]
                    for side in ("up","down","left","right"):
                        if csv_rooms.is_open_between(y, x, side):
                            r.doors.add(side)
            self.start_room = self.grid[self.rows//2][self.cols//2]
        else:
            # fallback: single empty room
            self.cols = self.rows = 1
            import numpy as np
            block = np.zeros((ROOM_TILES_H, ROOM_TILES_W), dtype=int)
            self.grid = [[Room(0, 0, block)]]
            self.start_room = self.grid[0][0]

    def neighbor(self, room: Room, side: str):
        dx, dy = DIRS[side]
        nx, ny = room.gx + dx, room.gy + dy
        if 0 <= nx < self.cols and 0 <= ny < self.rows:
            here = self.grid[room.gy][room.gx]
            there = self.grid[ny][nx]
            opposite = {"up":"down","down":"up","left":"right","right":"left"}[side]
            if (side in here.doors) and (opposite in there.doors):
                return there
        return None

    def find_door_transition(self, room: Room, player_rect: pygame.Rect):
        for rect, side in room.door_transition_rects():
            if player_rect.colliderect(rect):
                return side
        return None
