# support.py
import os, pygame

def import_folder(path: str):
    """Load all images in a folder, sorted by filename."""
    frames = []
    if not os.path.isdir(path):
        return frames
    for fname in sorted(os.listdir(path)):
        fpath = os.path.join(path, fname)
        if os.path.isdir(fpath):
            continue
        try:
            frames.append(pygame.image.load(fpath).convert_alpha())
        except Exception:
            pass
    return frames

def load_anim_set(base_dir: str, states: list[str]):
    """Return {state: [frames]} loaded from base_dir/<state>/*.png"""
    return {st: import_folder(os.path.join(base_dir, st)) for st in states}

def scale_frames(frames, scale: float):
    """Return a new list with all frames scaled by 'scale' (keeps per-pixel alpha)."""
    if scale == 1.0:
        return frames
    out = []
    for f in frames:
        w, h = f.get_width(), f.get_height()
        out.append(pygame.transform.smoothscale(f, (int(w*scale), int(h*scale))))
    return out
