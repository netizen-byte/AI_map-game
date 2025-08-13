# constants.py

# ----- Tiles & Room -----
TILE_SIZE = 32
ROOM_TILES_W = 16
ROOM_TILES_H = 16
ROOM_PIX_W = ROOM_TILES_W * TILE_SIZE
ROOM_PIX_H = ROOM_TILES_H * TILE_SIZE

# Screen = exactly one room (classic GB room feel)
SCREEN_WIDTH  = ROOM_PIX_W
SCREEN_HEIGHT = ROOM_PIX_H
FPS = 60

# Dungeon grid (rooms connected in a grid)
# Expanded to a 5x5 maze of rooms for a more intricate layout
DUNGEON_COLS = 5
DUNGEON_ROWS = 5

# ----- Fog of War -----
FOG_RADIUS = 96            # radius of visible circle around player (pixels)
FOG_ALPHA = 120            # darkness strength (0 transparent, 255 opaque)

# ----- Colors (fallback drawing if you don’t use tile images) -----
COLOR_FLOOR   = (42, 45, 60)
COLOR_WALL    = (25, 30, 40)
COLOR_DOOR    = (140, 120, 64)
COLOR_PLAYER  = (60, 200, 120)

# ----- Tile IDs -----
TILE_EMPTY = 0
TILE_WALL  = 1
TILE_FLOOR = 2
TILE_DOOR  = 3

# ----- Animation -----
ANIMATION_FPS = 8

# ----- Player stats / combat -----
PLAYER_SPEED = 200 
PLAYER_MAX_HP = 20
PLAYER_MAX_STAMINA = 100
STAMINA_COST_ATTACK = 25
STAMINA_REGEN_PER_SEC = 20
IFRAME_TIME = 0.6  # seconds of invulnerability after being hit
HIT_KNOCKBACK_SPEED = 260.0  # px/sec initial knockback push
HIT_KNOCKBACK_TIME  = 0.18   # seconds knockback decays to zero

# ----- Attack System -----
ATTACK_COOLDOWN = 0.2  # seconds between attacks - decrease for faster attacks
ATTACK_DURATION = 0.01  # how long attack animation lasts
ATTACK_DAMAGE = 3     # base attack damage
ATTACK_RANGE = 50      # attack reach in pixels

# ----- Traps -----
# Damage dealt when entering a trapped room
TRAP_DAMAGE = 2

# (future) path if you later want Tiled maps
MAPS_PATH = "maps"
