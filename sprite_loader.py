# sprite_loader.py
import os
import re
import pygame

SPRITES_PATH = "sprites"

# ===== helpers =====

def _load_strip_square(path: str) -> list[pygame.Surface]:
    """Split a horizontal strip into square frames (assumes frames are square:
       frame_w == sheet_h). Works great for 32x(32*N) sheets."""
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except Exception:
        return []
    h = sheet.get_height()
    if h <= 0:
        return []
    count = max(1, sheet.get_width() // h)
    frames = []
    for i in range(count):
        frame = pygame.Surface((h, h), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), pygame.Rect(i * h, 0, h, h))
        frames.append(frame)
    return frames

def _center_to_canvas(animations: dict[str, list[pygame.Surface]], scale: float = 1.0) -> dict[str, list[pygame.Surface]]:
    """Scale frames (uniformly) and paste them onto a common canvas so origins match."""
    # find largest frame size
    max_w = 0
    max_h = 0
    for frames in animations.values():
        for f in frames:
            w = int(round(f.get_width()  * scale))
            h = int(round(f.get_height() * scale))
            if w > max_w: max_w = w
            if h > max_h: max_h = h
    if max_w == 0 or max_h == 0:
        return animations

    out: dict[str, list[pygame.Surface]] = {}
    for key, frames in animations.items():
        new_list = []
        for f in frames:
            if scale != 1.0:
                f = pygame.transform.smoothscale(f, (int(round(f.get_width()*scale)),
                                                     int(round(f.get_height()*scale))))
            canvas = pygame.Surface((max_w, max_h), pygame.SRCALPHA)
            canvas.blit(f, ((max_w - f.get_width()) // 2,
                            (max_h - f.get_height()) // 2))
            new_list.append(canvas)
        out[key] = new_list
    return out

# ===== loader =====

class SpriteLoader:
    def __init__(self):
        self.cache = {}

    def _load_pack_char_star(self) -> dict[str, list[pygame.Surface]]:
        """Old pack: char_<state>_<dir>_anim_strip_N.png"""
        key = "pack_char_star_v1"
        if key in self.cache:
            return self.cache[key]

        states = ["idle", "walk", "attack", "hit"]
        dirs = ["down", "left", "right", "up"]
        found: dict[str, list[pygame.Surface]] = {}

        if os.path.isdir(SPRITES_PATH):
            for fname in os.listdir(SPRITES_PATH):
                m = re.match(r"char_([a-z]+)_([a-z]+)_anim_strip_(\d+)\.(png|bmp)$", fname, re.I)
                if not m:
                    continue
                st, dr, cnt = m.group(1).lower(), m.group(2).lower(), int(m.group(3))
                if st not in states or dr not in dirs:
                    continue
                path = os.path.join(SPRITES_PATH, fname)
                sheet = pygame.image.load(path).convert_alpha()
                fw = sheet.get_width() // cnt
                fh = sheet.get_height()
                frames = []
                for i in range(cnt):
                    fr = pygame.Surface((fw, fh), pygame.SRCALPHA)
                    fr.blit(sheet, (0, 0), pygame.Rect(i*fw, 0, fw, fh))
                    frames.append(fr)
                found[f"{st}_{dr}"] = frames

        # fallbacks per dir
        for dr in ["down", "left", "right", "up"]:
            if f"idle_{dr}" not in found:
                # minimal placeholder if literally nothing
                ph = pygame.Surface((16, 16), pygame.SRCALPHA); ph.fill((255,0,255))
                found[f"idle_{dr}"] = [ph]
            # if walk/attack/hit missing, fall back to idle
            for st in ["walk","attack","hit"]:
                found.setdefault(f"{st}_{dr}", found[f"idle_{dr}"])

        # scale this pack to 2x by default (these sheets are often small)
        found = _center_to_canvas(found, scale=2.0)
        self.cache[key] = found
        return found

    def _load_pack_redhair(self) -> dict[str, list[pygame.Surface]]:
        """Your new pack: specific filenames in /sprites:
           Staystill.png, Stay_still_back.png, Stay_still_left_.png, Stay_still_right.png,
           Walk_forward.png, Walk_up.png, Walk_left.png, Walk_right.png, (optional Die.png)
        """
        key = "pack_redhair_v1"
        if key in self.cache:
            return self.cache[key]

        p = lambda name: os.path.join(SPRITES_PATH, name)

        # idle strips (some sheets have 4 frames of standing; that’s fine)
        idle_down  = _load_strip_square(p("Staystill.png"))
        idle_up    = _load_strip_square(p("Stay_still_back.png"))
        idle_left  = _load_strip_square(p("Stay_still_left_.png")) or _load_strip_square(p("Stay_still_left.png"))
        idle_right = _load_strip_square(p("Stay_still_right.png"))

        # walk strips
        walk_down  = _load_strip_square(p("Walk_forward.png"))
        walk_up    = _load_strip_square(p("Walk_up.png"))
        walk_left  = _load_strip_square(p("Walk_left.png"))
        walk_right = _load_strip_square(p("Walk_right.png"))

        # optional death (not used by player yet, but we’ll keep it)
        die = _load_strip_square(p("Die.png"))

        anims: dict[str, list[pygame.Surface]] = {}

        # build state_dir keys used by player.py
        anims["idle_down"]  = idle_down  or [pygame.Surface((16,16), pygame.SRCALPHA)]
        anims["idle_up"]    = idle_up    or anims["idle_down"]
        anims["idle_left"]  = idle_left  or anims["idle_down"]
        anims["idle_right"] = idle_right or anims["idle_down"]

        anims["walk_down"]  = walk_down  or anims["idle_down"]
        anims["walk_up"]    = walk_up    or anims["idle_up"]
        anims["walk_left"]  = walk_left  or anims["idle_left"]
        anims["walk_right"] = walk_right or anims["idle_right"]

        # We don’t have attack/hit in this pack → fall back to idle of each dir
        for dr in ["down","up","left","right"]:
            anims[f"attack_{dr}"] = anims[f"idle_{dr}"]
            anims[f"hit_{dr}"]    = anims[f"idle_{dr}"]

        # keep original 1.0 scale (these sheets look 32×32), but center on common canvas
        anims = _center_to_canvas(anims, scale=1.0)

        # (optional) store death frames for later use
        if die:
            anims["die"] = _center_to_canvas({"die": die}, scale=1.0)["die"]

        self.cache[key] = anims
        return anims

    def load_player_animations(self) -> dict[str, list[pygame.Surface]]:
        """Auto-detect which pack you have and return animations that player.py expects."""
        # detect the new pack first (your filenames)
        if os.path.exists(os.path.join(SPRITES_PATH, "Staystill.png")):
            return self._load_pack_redhair()

        # else try the old char_* convention
        for fname in os.listdir(SPRITES_PATH) if os.path.isdir(SPRITES_PATH) else []:
            if re.match(r"char_([a-z]+)_([a-z]+)_anim_strip_(\d+)\.(png|bmp)$", fname, re.I):
                return self._load_pack_char_star()

        # absolute fallback: tiny magenta squares
        ph = pygame.Surface((16, 16), pygame.SRCALPHA); ph.fill((255, 0, 255))
        d = {}
        for st in ["idle","walk","attack","hit"]:
            for dr in ["down","up","left","right"]:
                d[f"{st}_{dr}"] = [ph.copy()]
        return _center_to_canvas(d, scale=1.0)

# singleton
sprite_loader = SpriteLoader()
