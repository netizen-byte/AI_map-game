# --- screen & timing ---
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
ANIM_FPS = 8

# --- world scale ---
TILE = 32                 # tile size used by your art & Tiled rooms
PLAYER_SPEED = 140        # pixels per second

# --- colours (only used by the prompt UI) ---
BG = (18, 22, 28)
UI_BG = (18, 18, 22, 230)
UI_BORDER = (230, 230, 255)
UI_TEXT = (240, 240, 255)
UI_HILITE = (255, 226, 120)

# --- gameplay ---
PLAYER_MAX_HP = 5
HAZARD_DAMAGE = 1
HAZARD_TICK_SECONDS = 0.6
HAZARD_GIDS = {82, 383}
BOMB_GIDS = {349}
BOMB_KILL_DELAY = 0.25

LAMP_TILE_GIDS = {78}   # e.g. {312, 313}  ← put your torch GIDs here
TRAP_TILE_GIDS = {82}

ANIM_FPS = 8