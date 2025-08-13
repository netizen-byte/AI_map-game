# sprite_loader.py
import pygame, os, re

SPRITES_PATH = "sprites"  # your character strips folder

class SpriteLoader:
    def __init__(self):
        self.cache = {}

    def load_player_animations(self):
        """
        Looks for files named:
          char_<state>_<dir>_anim_strip_<n>.png
        <state> in {idle, walk, attack, hit}, <dir> in {down,left,right,up}
        Every frame is scaled 2x and centered on a fixed canvas so the sprite won't wobble.
        """
        cache_key = "player_animations_v3"
        if cache_key in self.cache:
            return self.cache[cache_key]

        states = ["idle", "walk", "attack", "hit"]
        dirs   = ["down", "left", "right", "up"]
        found = []  # (state, dir, strip, fw, fh, count)

        os.makedirs(SPRITES_PATH, exist_ok=True)
        for fname in os.listdir(SPRITES_PATH):
            m = re.match(r"char_([a-z]+)_([a-z]+)_anim_strip_(\d+)\.(png|bmp)$", fname, re.I)
            if not m:
                continue
            st, dr, cnt = m.group(1).lower(), m.group(2).lower(), int(m.group(3))
            if st not in states or dr not in dirs:
                continue
            strip = pygame.image.load(os.path.join(SPRITES_PATH, fname)).convert_alpha()
            fw = strip.get_width() // cnt
            fh = strip.get_height()
            found.append((st, dr, strip, fw, fh, cnt))

        # Placeholder if nothing found
        if not found:
            ph = pygame.Surface((16, 16), pygame.SRCALPHA); ph.fill((255, 0, 255))
            d = {f"{st}_{dr}": [ph.copy()] for st in states for dr in dirs}
            self.cache[cache_key] = d
            return d

        # Choose common canvas from largest frame (keeps origin steady)
        scale = 2
        max_w = max(fw for *_a, fw, _b, _c in found) * scale
        max_h = max(fh for *_a, _b, fh, _c in found) * scale

        anims = {}
        for st, dr, strip, fw, fh, cnt in found:
            frames = []
            for i in range(cnt):
                src = pygame.Surface((fw, fh), pygame.SRCALPHA)
                src.blit(strip, (0, 0), pygame.Rect(i*fw, 0, fw, fh))
                scaled = pygame.transform.scale(src, (fw*scale, fh*scale))
                canvas = pygame.Surface((max_w, max_h), pygame.SRCALPHA)
                canvas.blit(scaled, ((max_w - scaled.get_width()) // 2,
                                     (max_h - scaled.get_height()) // 2))
                frames.append(canvas)
            anims[f"{st}_{dr}"] = frames

        # Fallbacks for any missing combos
        for st in states:
            for dr in dirs:
                k = f"{st}_{dr}"
                if k not in anims:
                    anims[k] = anims.get(f"idle_{dr}") or anims.get(f"walk_{dr}") or anims.get(f"attack_{dr}") or anims.get(f"hit_{dr}")

        self.cache[cache_key] = anims
        return anims

sprite_loader = SpriteLoader()
