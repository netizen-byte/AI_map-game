# full_map.py
from pathlib import Path
import numpy as np
import pygame

# --- CONFIG ---
TILE_SIZE = 32
# ONLY these tiles are walkable (your 8 floor tiles)
WALKABLE_TILES = {1,2,3,4,5,6,7,8}

# Filenames (adjust if yours differ)
CSV_BASE = "ai project map._Tile Layer 1.csv"
CSV_DOOR = "ai project map._door.csv"
TILESET  = "Full.png"  # tileset image (searched in sprites_en/, assets/, maps/, .)

def _load_csv(path: Path) -> np.ndarray:
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append([int(x) for x in line.split(",")])
    return np.array(rows, dtype=int)

def _slice_tiles(tileset_surf: pygame.Surface, tile_size: int) -> list[pygame.Surface]:
    w, h = tileset_surf.get_width(), tileset_surf.get_height()
    tx, ty = w // tile_size, h // tile_size
    tiles = []
    for yy in range(ty):
        for xx in range(tx):
            r = pygame.Rect(xx*tile_size, yy*tile_size, tile_size, tile_size)
            tiles.append(tileset_surf.subsurface(r))
    return tiles

class FullMap:
    """
    Loads the big CSV, renders everything to an offscreen surface,
    provides tile collision + door teleport helpers.
    """
    def __init__(self, maps_dir: str | Path = "maps", assets_dirs: list[str|Path] | None = None):
        maps_dir = Path(maps_dir)
        if assets_dirs is None:
            assets_dirs = [maps_dir, Path("sprites_en"), Path("assets"), Path("maps"), Path(".")]

        # --- base (required) ---
        base_path = maps_dir / CSV_BASE
        if not base_path.exists():
            raise FileNotFoundError(f"Base CSV not found: {base_path}")
        self.base = _load_csv(base_path)     # -1 = empty
        self.h, self.w = self.base.shape     # tiles

        # --- door layer (optional; pad/crop to match base) ---
        door_path = maps_dir / CSV_DOOR
        if door_path.exists():
            raw = _load_csv(door_path)
            # pad/crop to base shape to avoid IndexError
            doors = np.full(self.base.shape, -1, dtype=int)
            h = min(self.h, raw.shape[0])
            w = min(self.w, raw.shape[1])
            doors[:h, :w] = raw[:h, :w]
            self.doors = doors
        else:
            self.doors = np.full(self.base.shape, -1, dtype=int)

        # --- find tileset image ---
        surf = None
        for folder in assets_dirs:
            p = Path(folder) / TILESET
            if p.exists():
                surf = pygame.image.load(p.as_posix()).convert_alpha()
                break
        if surf is None:
            raise FileNotFoundError(f"Tileset '{TILESET}' not found in {assets_dirs}")
        self.tiles = _slice_tiles(surf, TILE_SIZE)

        # pre-render world
        self.world_px = self.w * TILE_SIZE
        self.world_py = self.h * TILE_SIZE
        self.world_surface = pygame.Surface((self.world_px, self.world_py), pygame.SRCALPHA)
        self._render_world()

        # collect door rects
        self.door_rects: list[pygame.Rect] = []
        for ty in range(self.h):
            for tx in range(self.w):
                if self.doors[ty, tx] != -1:
                    self.door_rects.append(pygame.Rect(tx*TILE_SIZE, ty*TILE_SIZE, TILE_SIZE, TILE_SIZE))

    # ---------- logic ----------
    def is_walkable_tile(self, tx: int, ty: int) -> bool:
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return False
        tid = self.base[ty, tx]
        if tid == -1:
            return False
        return tid in WALKABLE_TILES

    def rect_collides(self, rect: pygame.Rect) -> bool:
        left   = max(0, rect.left // TILE_SIZE)
        right  = min(self.w-1, (rect.right-1) // TILE_SIZE)
        top    = max(0, rect.top // TILE_SIZE)
        bottom = min(self.h-1, (rect.bottom-1) // TILE_SIZE)
        for ty in range(top, bottom+1):
            for tx in range(left, right+1):
                if not self.is_walkable_tile(tx, ty):
                    if rect.colliderect(pygame.Rect(tx*TILE_SIZE, ty*TILE_SIZE, TILE_SIZE, TILE_SIZE)):
                        return True
        return False

    def door_hit(self, rect: pygame.Rect) -> pygame.Rect | None:
        for r in self.door_rects:
            if rect.colliderect(r):
                return r
        return None

    def random_other_door_center(self, forbid_rect: pygame.Rect) -> tuple[int,int] | None:
        import random
        candidates = [r for r in self.door_rects if r is not forbid_rect]
        if not candidates:
            return None
        r = random.choice(candidates)
        return r.center

    # ---------- drawing ----------
    def _render_world(self):
        ws = self.world_surface
        ws.fill((0,0,0,0))
        for ty in range(self.h):
            for tx in range(self.w):
                tid = self.base[ty, tx]
                if 0 <= tid < len(self.tiles):
                    ws.blit(self.tiles[tid], (tx*TILE_SIZE, ty*TILE_SIZE))

    def draw_scaled_fit(self, screen: pygame.Surface):
        """Draw entire map scaled to fit into current window size; returns (scale, ox, oy)."""
        sw, sh = screen.get_size()
        sx = sw / self.world_px
        sy = sh / self.world_py
        scale = min(sx, sy)
        new_w = max(1, int(self.world_px * scale))
        new_h = max(1, int(self.world_py * scale))
        scaled = pygame.transform.smoothscale(self.world_surface, (new_w, new_h))
        ox = (sw - new_w) // 2
        oy = (sh - new_h) // 2
        screen.blit(scaled, (ox, oy))
        return scale, ox, oy
