from __future__ import annotations
import json, re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from constants import TILE, HAZARD_GIDS, BOMB_GIDS
from constants import LAMP_TILE_GIDS, TRAP_TILE_GIDS, ANIM_FPS
import pygame
from pathlib import Path

# Try to import a global animation FPS, fallback to 8 if not defined
try:
    from constants import ANIM_FPS as _GLOBAL_ANIM_FPS
except Exception:
    _GLOBAL_ANIM_FPS = 8

# New: keys that mark a door layer (doors are walkable, but detected)
DOOR_LAYER_KEYS = ("door", "doors")
DECOR_LAYER_KEYS = ("decor", "decoration")
HAZARD_LAYER_KEYS = ("lava", "trap", "hazard")
SPAWN_LAYER_KEYS = ("player_spawn", "spawn")
BACK_SPAWN_LAYER_KEYS = ("back_from_other_room", "return_spawn")  # lowercase for matching
SPAWN_IDLE_ANIMS = ("Staystill", "idle_front", "idle_down", "front_idle")  # preferred idle names

# --- collision rules ---
# Door (object PNG) should be walkable:
OBJECT_WHITELIST = {"34.png"}              # the arch/door PNG in /objects

# These object PNGs should be SOLID (not walkable):
OBJECT_BLOCKLIST = {
    "42.png",  # small statue
    "43.png",  # cracked/bigger statue
    "44.png",  # small banner
    "45.png",  # medium banner
    "46.png",  # big banner
    "47.png",  # pillar
}

# If you also use the door from the atlas (Full.png) instead of /objects,
# keep this so atlas door is walkable too (adjust id if yours differs).
DECOR_ATLAS_WHITELIST = {34}               # walkable atlas-tile ids (e.g., door arch)


# ---------- simple data container ----------
@dataclass
class Room:
    surf: pygame.Surface
    pixel_size: Tuple[int, int]
    floor_cells: List[Tuple[int, int]] = field(default_factory=list)
    door_cells:  List[Tuple[int, int]] = field(default_factory=list)
    solids:      List[pygame.Rect]     = field(default_factory=list)
    dynamic_solids: List[pygame.Rect]  = field(default_factory=list)
    spawn_override: Tuple[int,int] | None = None  # NEW: explicit spawn point
    back_spawn_override: Tuple[int,int] | None = None  # NEW
    hazards:     List[pygame.Rect]     = field(default_factory=list)  # NEW: hazard rects
    bombs:       List[pygame.Rect]     = field(default_factory=list)  # NEW: bomb rects

    # NEW: animated overlay objects (e.g., torches, traps)
    # Each entry: {"rect": pygame.Rect, "frames": [Surface,...], "fps": int}
    animated_objects: list = field(default_factory=list)

    # draw pre-rendered room + animated overlays
    def draw(self, screen: pygame.Surface, offset: Tuple[int, int]) -> None:
        screen.blit(self.surf, offset)

        if not self.animated_objects:
            return

        # Current animation tick
        ticks = pygame.time.get_ticks()
        for obj in self.animated_objects:
            frames: list[pygame.Surface] = obj.get("frames") or []
            fps: int = int(obj.get("fps") or _GLOBAL_ANIM_FPS or 8)
            rect: pygame.Rect = obj["rect"]

            if not frames:
                # Fallback: subtle alpha pulse if frames missing
                # (keeps things visible even if sprite not found)
                pulse = (pygame.math.sin(ticks * 0.005) + 1.0) * 0.25 + 0.5  # 0.5..1.0
                tmp = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                tmp.fill((255, 255, 255, int(255 * pulse)))
                screen.blit(tmp, (rect.x - offset[0], rect.y - offset[1]))
                continue

            # Advance frame based on time
            period_ms = max(1, int(1000 / max(1, fps)))
            idx = (ticks // period_ms) % len(frames)
            img = frames[idx]
            screen.blit(img, (rect.x - offset[0], rect.y - offset[1]))

    # door rectangles (world coords; shift by offset for screen coords)
    def door_rects(self, offset: Tuple[int,int]|None=None) -> List[pygame.Rect]:
        rects = [pygame.Rect(x*TILE, y*TILE, TILE, TILE) for x,y in self.door_cells]
        if offset is None: return rects
        ox, oy = offset; return [r.move(-ox, -oy) for r in rects]

    # hazard rectangles similar to doors
    def hazard_rects(self, offset: Tuple[int,int]|None=None) -> List[pygame.Rect]:
        rects = [pygame.Rect(r.x, r.y, r.w, r.h) for r in self.hazards]
        if offset is None: return rects
        ox, oy = offset; return [r.move(-ox, -oy) for r in rects]

    def bomb_rects(self, offset: Tuple[int,int]|None=None) -> List[pygame.Rect]:
        rects = [pygame.Rect(r.x, r.y, r.w, r.h) for r in self.bombs]
        if offset is None: return rects
        ox, oy = offset; return [r.move(-ox, -oy) for r in rects]

    # floor cell centres (world coords)
    def floor_positions(self) -> List[Tuple[int,int]]:
        return [ (int((x+0.5)*TILE), int((y+0.5)*TILE)) for x,y in self.floor_cells ]

    def get_spawn_point(self, prefer_back: bool=False) -> Tuple[int, int]:
        # NEW: prefer explicit back spawn if requested
        if prefer_back and self.back_spawn_override:
            return self.back_spawn_override
        if self.spawn_override:
            return self.spawn_override
        """Centre of mass of floor cells; always inside the room."""
        pos = self.floor_positions()
        if pos:
            ax = sum(x for x,_ in pos) / len(pos)
            ay = sum(y for _,y in pos) / len(pos)
            return int(ax), int(ay)
        w,h = self.pixel_size
        return w//2, h//2

    # collision rects (optionally shifted to screen coords by -offset)
    def solid_rects(self, offset: Tuple[int,int]|None=None) -> List[pygame.Rect]:
        # merged static + dynamic
        rects = self.solids + (self.dynamic_solids if self.dynamic_solids else [])
        if offset is None:
            return rects
        ox, oy = offset
        return [r.move(-ox, -oy) for r in rects]


class RoomMap:
    """Load pre-rendered room from a single Tiled JSON file."""
    def __init__(self, maps_dir: str="maps", sprites_dir: str="sprites_en"):
        self.maps_dir = Path(maps_dir).resolve()
        self.sprites_dir = Path(sprites_dir).resolve()
        self._placed_atlas: list = []
        self._placed_objects: list = []
        self._rebuilt_solids: list[pygame.Rect] = []
        self._solids_dirty: bool = False  # new flag
        self.current_room: Room | None = None  # NEW

        # NEW: cache of sliced animation frames by filename
        self._anim_cache: dict[str, list[pygame.Surface]] = {}

    @staticmethod
    def _is(layer_name: str, needle: str) -> bool:
        return needle.lower() in layer_name.lower()

    @staticmethod
    def _gid_to_xy(i: int, width: int) -> Tuple[int,int]:
        return i % width, i // width

    @staticmethod
    
    def _slice_square_strip(sheet: pygame.Surface) -> list[pygame.Surface]:
        """Split a horizontal strip into square frames (frame_w == sheet_h)."""
        h = sheet.get_height()
        if h <= 0:
            return [sheet]
        count = max(1, sheet.get_width() // h)
        frames = []
        for i in range(count):
            r = pygame.Rect(i * h, 0, h, h)
            frames.append(sheet.subsurface(r).copy())
        return frames

    def _load_external_tsx_image(self, tsx_path: Path) -> Path|None:
        if not tsx_path.exists(): return None
        text = tsx_path.read_text(encoding="utf-8")
        m = re.search(r'image source="([^"]+)"', text)
        if not m: return None
        return (tsx_path.parent / m.group(1)).resolve()

    def load_json_room(self, filename: str, player=None) -> Room:  # added optional player
        json_path = (self.maps_dir / filename).resolve()
        data = json.loads(json_path.read_text(encoding="utf-8"))

        tw, th = data["tilewidth"], data["tileheight"]
        w_tiles, h_tiles = data["width"], data["height"]
        room_px = (w_tiles*tw, h_tiles*th)

        # Load all tileset atlases referenced by the map
        atlases: list[pygame.Surface|None] = []
        bases:    list[int] = []
        ts_defs   = data.get("tilesets", [])
        # Build helper map: global gid -> per-tile image filename (for image collection tilesets)
        gid_to_image: dict[int, str] = {}
        for ts in ts_defs:
            bases.append(ts["firstgid"])
            atlas_path: Path|None = None

            if "image" in ts:  # embedded image
                atlas_path = (json_path.parent / ts["image"]).resolve()
                image_name = Path(ts["image"]).name
            elif "source" in ts:  # external TSX → parse to find the image
                tsx_path = (json_path.parent / ts["source"]).resolve()
                img_from_tsx = self._load_external_tsx_image(tsx_path)
                atlas_path = img_from_tsx if img_from_tsx else None
                image_name = Path(img_from_tsx).name if img_from_tsx else None
            else:
                image_name = None

            # If the resolved path doesn't exist (e.g., local Downloads path), try fallbacks by filename
            if not (atlas_path and atlas_path.exists()):
                candidate_dirs = [
                    json_path.parent,
                    Path("sprites_en").resolve(),
                    Path("assets").resolve(),
                    Path("maps").resolve(),
                    Path(".").resolve(),
                ]
                if image_name:
                    stem = Path(image_name).stem
                    # try exact name first, then alternate extensions with same stem
                    alt_exts = [".png", ".webp", ".jpg", ".jpeg"]
                    for folder in candidate_dirs:
                        # exact match
                        cand = (folder / image_name)
                        if cand.exists():
                            atlas_path = cand.resolve()
                            break
                        # extension-agnostic match
                        for ext in alt_exts:
                            alt = (folder / f"{stem}{ext}")
                            if alt.exists():
                                atlas_path = alt.resolve()
                                break
                        if atlas_path and atlas_path.exists():
                            break

            if atlas_path and atlas_path.exists():
                atlases.append(pygame.image.load(atlas_path.as_posix()).convert_alpha())
            else:
                atlases.append(None)  # missing image is fine; we just don't blit

            # Map individual tile images if present
            for tile_def in ts.get("tiles", []) or []:
                local_id = tile_def.get("id")
                img = tile_def.get("image")
                if local_id is None or not img:
                    continue
                global_gid = ts["firstgid"] + local_id
                gid_to_image[global_gid] = Path(img).name

        # quick helper to pick atlas by gid
        def pick_atlas(gid: int):
            idx = max(i for i, base in enumerate(bases) if gid >= base)
            return idx, atlases[idx], bases[idx]

        # Pre-render all tiles to a surface and collect logic cells
        surf = pygame.Surface(room_px, pygame.SRCALPHA)
        floor_cells: list[tuple[int,int]] = []
        door_cells : list[tuple[int,int]] = []
        solid_cells: list[tuple[int,int]] = []
        spawn_cells: list[tuple[int,int]] = []  # NEW
        back_spawn_cells: list[tuple[int,int]] = []  # NEW
        object_solids: list[pygame.Rect] = []  # moved: now for all rooms
        hazards: list[pygame.Rect] = []       # NEW
        bombs: list[pygame.Rect] = []
        animated_objects: list = []           # NEW: torch/trap renderers

        for layer in data["layers"]:
            ltype = layer.get("type")
            if ltype == "tilelayer":
                name = layer.get("name", "")
                lname = name.lower()
                grid = layer["data"]
                width = layer["width"]

                is_spawn_layer = any(k in lname for k in SPAWN_LAYER_KEYS)
                is_back_spawn_layer = any(k in lname for k in BACK_SPAWN_LAYER_KEYS)

                for i, gid in enumerate(grid):
                    if gid == 0: continue
                    x, y = self._gid_to_xy(i, width)

                    if is_spawn_layer:
                        spawn_cells.append((x, y)); continue
                    if is_back_spawn_layer:
                        back_spawn_cells.append((x, y)); continue

                    # blit (unchanged)
                    atlas_i, atlas, base = pick_atlas(gid)
                    if atlas is not None:
                        ts_def = ts_defs[atlas_i]
                        ltw = ts_def.get("tilewidth", tw)
                        lth = ts_def.get("tileheight", th)
                        cols = atlas.get_width() // ltw
                        local = gid - base
                        sx = (local % cols) * ltw
                        sy = (local // cols) * lth
                        surf.blit(atlas, pygame.Rect(x*tw, y*th, ltw, lth),
                                  pygame.Rect(sx, sy, ltw, lth))

                    # logic classification
                    tile_rect = pygame.Rect(x*tw, y*th, tw, th)
                    if self._is(name, "floor"):
                        floor_cells.append((x, y))
                    elif any(k in lname for k in DOOR_LAYER_KEYS):
                        door_cells.append((x, y))
                    elif gid in HAZARD_GIDS:
                        hazards.append(tile_rect)
                    elif gid in BOMB_GIDS:
                        hazards.append(tile_rect)
                        bombs.append(tile_rect.inflate(1, 1))
                    elif any(k in lname for k in HAZARD_LAYER_KEYS):   # layer named "trap/lava/hazard"
                        hazards.append(tile_rect)
                    elif any(k in lname for k in DECOR_LAYER_KEYS):
                        pass
                    elif "wall" in lname or "solid" in lname:
                        solid_cells.append((x, y))
                    else:
                        pass

                    # --- NEW: animated torch/trap overlays by image filename ---
                    img_name = (gid_to_image.get(gid) or "").lower()
                    if img_name in ("lamp.png", "trap.png"):
                        # Load and slice once; reuse from cache
                        frames = self._anim_cache.get(img_name) 
                        if not frames:
                            sheet_path = Path("sprites") / img_name
                            if sheet_path.exists():
                                try:
                                    sheet = pygame.image.load(sheet_path.as_posix()).convert_alpha()
                                    frames = self._slice_square_strip(sheet)
                                except Exception:
                                    frames = []
                            else:
                                frames = []
                            self._anim_cache[img_name] = frames

                        animated_objects.append({
                            "rect": tile_rect,
                            "frames": frames,
                            "fps": _GLOBAL_ANIM_FPS,
                        })

            elif ltype == "objectgroup":
                lname = layer.get("name", "").lower()
                if "object layer" in lname:
                    for obj in layer.get("objects", []):
                        x = obj.get("x", 0)
                        y = obj.get("y", 0)
                        w = obj.get("width", 0)
                        h = obj.get("height", 0)
                        # Tiled object y is top-left; create rect directly
                        r = pygame.Rect(int(x), int(y), int(w), int(h))
                        if r.width and r.height:
                            object_solids.append(r)
                        gid = obj.get("gid")
                        if gid:
                            img = gid_to_image.get(gid, "").lower()
                            if img.endswith("39.png") or img.endswith("40.png") or img.endswith("lamp.png") or img == "lava.png" or img == "volcanoe_tiles.png":
                                hazards.append(r.copy())
                            if img == "icon41.png":
                                hazards.append(r.copy())
                                bombs.append(r.inflate(-6, -6))

        door_set = set(door_cells)

        # keep every solid except those that are doors
        solid_cells = [(x, y) for (x, y) in solid_cells if (x, y) not in door_set]
        solids = [pygame.Rect(x*TILE, y*TILE, TILE, TILE) for x, y in solid_cells]
        solids.extend(object_solids)  # include object layer solids globally

        # NEW: compute spawn_override if any spawn cells collected
        spawn_override = None
        if spawn_cells:
            # centre of all spawn tiles
            px = [ (x + 0.5) * TILE for x,_ in spawn_cells ]
            py = [ (y + 0.5) * TILE for _,y in spawn_cells ]
            spawn_override = (int(sum(px)/len(px)), int(sum(py)/len(py)))
        back_spawn_override = None  # NEW
        if back_spawn_cells:
            px = [ (x + 0.5) * TILE for x,_ in back_spawn_cells ]
            py = [ (y + 0.5) * TILE for _,y in back_spawn_cells ]
            back_spawn_override = (int(sum(px)/len(px)), int(sum(py)/len(py)))

        room = Room(
            surf=surf,
            pixel_size=room_px,
            floor_cells=floor_cells,
            door_cells=door_cells,
            solids=solids,
            spawn_override=spawn_override,
            back_spawn_override=back_spawn_override,  # NEW
            hazards=hazards,
            bombs=bombs,
            animated_objects=animated_objects,        # NEW
        )
        self.current_room = room  # NEW: track for dynamic solid updates
        if player is not None:
            self.apply_player_spawn(player)  # auto place & idle reset
        return room

    def _rebuild_solids(self):
        """Recreate solid rect list from placed atlas tiles and loose object PNGs."""
        solids: list[pygame.Rect] = []

        # --- SOLIDS FROM ATLAS-PLACED TILES ---
        for t in self._placed_atlas:
            tile_id = getattr(t, "gid", None) or getattr(t, "tile_id", None)
            if tile_id in DECOR_ATLAS_WHITELIST:
                continue  # whitelisted (e.g., door arch) -> walkable
            solids.append(t.rect)  # default atlas decor/walls -> solid

        # --- SOLIDS FROM LOOSE OBJECT PNGs (/objects) ---
        for o in self._placed_objects:
            src = getattr(o, "source", "") or getattr(o, "path", "")
            fname = src.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]  # normalize

            if fname in OBJECT_WHITELIST:
                continue  # walkable door object

            if fname in OBJECT_BLOCKLIST:
                solids.append(o.rect)
                continue

            # Optional: make all other objects solid:
            # solids.append(o.rect)

        self._rebuilt_solids = solids
        self._solids_dirty = False
        if self.current_room:
            self.current_room.dynamic_solids = solids  # push to room so room.solid_rects() includes them

    # --- NEW PUBLIC HELPERS -------------------------------------------------
    def add_object_placement(self, obj):
        """
        Register a placed object.
        obj must expose:
          - rect (pygame.Rect)
          - source or path (string ending with 'NN.png', e.g. '42.png')
        """
        self._placed_objects.append(obj)
        self._solids_dirty = True

    def add_atlas_tile(self, tile):
        """
        Register a placed atlas tile (dynamic decor/wall).
        tile must expose:
          - rect (pygame.Rect)
          - gid or tile_id (int)
        """
        self._placed_atlas.append(tile)
        self._solids_dirty = True

    def get_all_solid_rects(self, room: Room, offset: Tuple[int,int]|None=None) -> list[pygame.Rect]:
        if self._solids_dirty:
            self._rebuild_solids()
        return room.solid_rects(offset)  # unified

    def apply_player_spawn(self, player):
        """
        Position player at current room spawn and force idle/front animation.
        Call after room change if not using the player param in load_json_room.
        """
        if not self.current_room:
            return
        x, y = self.current_room.get_spawn_point()

        # Try rect-based placement first
        if hasattr(player, "rect") and isinstance(getattr(player, "rect"), pygame.Rect):
            player.rect.center = (x, y)
        else:
            # Fallback to x/y attributes if present
            if hasattr(player, "x"): setattr(player, "x", x)
            if hasattr(player, "y"): setattr(player, "y", y)

        # Optional facing direction standardization
        if hasattr(player, "facing"):
            player.facing = "down"

        self._reset_player_idle(player)

    def _reset_player_idle(self, player):
        """
        Force one of the preferred idle animations/states.
        Tries (in order):
         - player.set_state(name)
         - player.play(name)
         - setting player.animation / player.current_animation / player.state
        Stops at first success.
        """
        for name in SPAWN_IDLE_ANIMS:
            # set_state method
            if hasattr(player, "set_state"):
                try:
                    player.set_state(name)
                    return
                except Exception:
                    pass
            # play method (typical animation controller)
            if hasattr(player, "play"):
                try:
                    player.play(name)
                    return
                except Exception:
                    pass
            # direct attribute assignments
            for attr in ("animation", "current_animation", "state"):
                if hasattr(player, attr):
                    try:
                        setattr(player, attr, name)
                        return
                    except Exception:
                        continue
        # If nothing worked, silently ignore
