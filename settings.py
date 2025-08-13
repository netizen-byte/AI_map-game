# --- Enemy system settings ---

# Path to the monsters asset folder
ENEMY_ASSET_PATH = "monsters"

# Monster stats dictionary
MONSTER_DATA = {
    'squid': {
        'health': 100,
        'exp': 100,
        'damage': 20,
        'speed': 3,
        'resistance': 3,
        'attack_radius': 80,
        'notice_radius': 360,
        'attack_cooldown': 400
    },
    'raccoon': {
        'health': 300,
        'exp': 250,
        'damage': 40,
        'speed': 2,
        'resistance': 3,
        'attack_radius': 120,
        'notice_radius': 400,
        'attack_cooldown': 800
    },
    'spirit': {
        'health': 100,
        'exp': 110,
        'damage': 8,
        'speed': 3.2,
        'resistance': 3,
        'attack_radius': 60,
        'notice_radius': 350,
        'attack_cooldown': 500
    },
    'bamboo': {
        'health': 70,
        'exp': 120,
        'damage': 6,
        'speed': 2.8,
        'resistance': 3,
        'attack_radius': 50,
        'notice_radius': 300,
        'attack_cooldown': 450
    }
}

# Invulnerability time (ms) after enemy hit
ENEMY_INVULN_MS = 300

# Animation speed for enemy frames
ANIM_SPEED = 0.15

# --- Enemy visuals / spawn control ---
ENEMY_SCALE = 0.75          # <— shrink enemies (1.0 = original)
ENEMY_INVULN_MS = 300       # already present; leave as-is or tweak
ANIM_SPEED = 0.15           # already present; leave as-is

# Only spawn enemies in rooms listed here.
# Keys are (room_grid_x, room_grid_y) -> list of spawns:
#   ("monster_name", ("tile", tx, ty))  OR  ("monster_name", ("px", x, y))
ENEMY_SPAWNS = {
    # example spawns — change to your taste; remove if you want an empty dungeon
    (1, 1): [("bamboo", ("tile", 6, 6)), ("slime", ("tile", 10, 8))],
    (0, 2): [("spirit", ("px", 380, 220))],
    # (gx, gy): [...],
}

# Chance each listed spawn actually creates an enemy (lower = fewer spawns)
ENEMY_SPAWN_CHANCE = 0.35

