# enemy.py
# enemy.py (top)
import os, pygame
from entity import Entity
from support import load_anim_set, scale_frames
from settings import MONSTER_DATA, ENEMY_ASSET_PATH, ENEMY_INVULN_MS, ANIM_SPEED, ENEMY_SCALE


class Enemy(Entity):
    """Idle → notice → move → attack; invuln flicker; attack cooldown; HP bars."""
    def __init__(self, name, pos, groups, obstacle_sprites,
                 damage_player_cb, death_fx_cb, add_exp_cb):
        super().__init__(groups, obstacle_sprites)
        self.sprite_type = 'enemy'

        self.name = name if name in MONSTER_DATA else next(iter(MONSTER_DATA))
        data = MONSTER_DATA[self.name]
        self.max_health = data['health']
        self.health = self.max_health
        self.exp = data['exp']
        self.damage = data['damage']
        self.base_speed = data['speed'] * 60  # px/s feel
        self.resistance = data['resistance']
        self.attack_radius = data['attack_radius']
        self.notice_radius = data['notice_radius']
        self.attack_cooldown = data['attack_cooldown']

        self.animation_speed = ANIM_SPEED
        self.vulnerable = True
        self.hit_time = 0
        self.can_attack = True
        self.attack_time = 0
        self.status = 'idle'

        # Callbacks provided by Level/Game
        self.damage_player = damage_player_cb   # (amount, type, pos)
        self.death_fx = death_fx_cb
        self.add_exp = add_exp_cb

        # Load animations from monsters/<name>/{idle,move,attack}
        base_dir = os.path.join(ENEMY_ASSET_PATH, self.name)
        self.animations = load_anim_set(base_dir, ['idle','move','attack'])
        # fallbacks
        for k in self.animations:
            self.animations[k] = scale_frames(self.animations[k], ENEMY_SCALE)

        self.image = self.animations['idle'][0]
        self.image.set_alpha(255)  # ensure fully visible by default
        self.rect = self.image.get_rect(topleft=pos)
        # give a sensible hitbox inset based on new size
        inset_x = max(2, int(self.rect.width * 0.15))
        inset_y = max(2, int(self.rect.height * 0.28))
        self.hitbox = self.rect.inflate(-inset_x, -inset_y)


    # -------- AI ----------
    def _dist_dir_to(self, target_rect):
        e = pygame.math.Vector2(self.rect.center)
        t = pygame.math.Vector2(target_rect.center)
        dvec = t - e
        dist = dvec.length()
        return dist, (dvec.normalize() if dist > 0 else pygame.math.Vector2())

    def _get_status(self, player):
        d, _ = self._dist_dir_to(player.rect)
        if d <= self.attack_radius and self.can_attack:
            if self.status != 'attack': self.frame_index = 0
            self.status = 'attack'
        elif d <= self.notice_radius:
            self.status = 'move'
        else:
            self.status = 'idle'

    def _act(self, player):
        if self.status == 'attack':
            self.attack_time = pygame.time.get_ticks()
            self.can_attack = False
            self.direction.xy = (0,0)
            # Deal damage; pass our center for player knockback direction
            self.damage_player(self.damage, 'enemy', self.rect.center)
        elif self.status == 'move':
            self.direction = self._dist_dir_to(player.rect)[1]
        else:
            self.direction.xy = (0,0)

    # -------- Damage / death ----------
    def get_damage(self, player, attack_type='weapon'):
        if not self.vulnerable:
            return
        self.vulnerable = False
        self.hit_time = pygame.time.get_ticks()
        # damage: ask player API if present
        dmg = 1
        if attack_type == 'weapon' and hasattr(player, 'get_full_weapon_damage'):
            dmg = player.get_full_weapon_damage()
        elif attack_type != 'weapon' and hasattr(player, 'get_full_magic_damage'):
            dmg = player.get_full_magic_damage()
        self.health -= dmg
        # reaction push away from player
        _, dir_to_player = self._dist_dir_to(player.rect)
        self.direction = -dir_to_player * self.resistance

    def _cooldowns(self):
        now = pygame.time.get_ticks()
        if not self.can_attack and now - self.attack_time >= self.attack_cooldown:
            self.can_attack = True
        if not self.vulnerable and now - self.hit_time >= ENEMY_INVULN_MS:
            self.vulnerable = True

    def _animate(self):
        anim = self.animations[self.status]
        self.frame_index += self.animation_speed
        if int(self.frame_index) >= len(anim):
            self.frame_index = 0

        img = anim[int(self.frame_index)]

        if not self.vulnerable:
            # gentle flicker instead of invisible frames
            # oscillate alpha 180–255
            t = pygame.time.get_ticks()
            alpha = 180 + (75 if (t // 60) % 2 == 0 else 0)
            img = img.copy()
            img.set_alpha(alpha)
        else:
            # fully opaque when not hurt
            img = img.copy()
            img.set_alpha(255)

        self.image = img
        self.rect = self.image.get_rect(center=self.hitbox.center)

    def enemy_update(self, player):
        self._get_status(player)
        self._act(player)

    def update(self):
        if not self.vulnerable:
            self.direction *= 0.9
        self._cooldowns()
        self.move(self.base_speed)
        self._animate()
        if self.health <= 0:
            self.add_exp(self.exp)
            self.death_fx(self.rect.center, self.name)
            self.kill()

    def render_extras(self, surface):
        # small HP bar above enemy
        bw, bh = 26, 4
        bx = self.rect.centerx - bw // 2
        by = self.rect.top - 8
        pygame.draw.rect(surface, (30,30,40), (bx-1, by-1, bw+2, bh+2))
        fill = int(bw * max(0, self.health) / self.max_health)
        pygame.draw.rect(surface, (230,80,80), (bx, by, fill, bh))
