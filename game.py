import random
from pathlib import Path
from typing import List, Tuple, Optional

import pygame
from constants import SCREEN_W, SCREEN_H, FPS, TILE, PLAYER_MAX_HP, HAZARD_DAMAGE, HAZARD_TICK_SECONDS
from room_map import RoomMap
from player import Player



class TextBox:
    """Flexible text panel. Can be used as a simple message or a Y/N confirm.

    API:
      show(text, confirm=False, on_yes=None, on_no=None)

    For compatibility the old name `ConfirmBox` is kept as an alias.
    """
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.active = False
        self.text = ""
        self.confirm_mode = False
        self.on_yes = None
        self.on_no = None
        self.confirm_hint = None

        # visual config
        self.bg = (24, 26, 30)
        self.border = (110, 110, 130)
        self.text_color = (235, 235, 240)
        self.shadow = (6, 8, 12)

    def show(self, text: str, confirm: bool = False, on_yes=None, on_no=None, confirm_hint: str | None = None):
        self.active = True
        self.text = text
        self.confirm_mode = confirm
        self.on_yes = on_yes
        self.on_no = on_no
        self.confirm_hint = confirm_hint

    def cancel(self):
        self.active = False
        self.text = ""
        self.confirm_mode = False
        self.on_yes = None
        self.on_no = None

    def handle_event(self, ev: pygame.event.Event):
        if not self.active:
            return
        if ev.type == pygame.KEYDOWN:
            if self.confirm_mode:
                if ev.key in (pygame.K_y, pygame.K_RETURN, pygame.K_e):
                    cb = self.on_yes
                    self.cancel()
                    if cb:
                        cb()
                elif ev.key in (pygame.K_n, pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    cb = self.on_no
                    self.cancel()
                    if cb:
                        cb()
            else:
                self.cancel()

    def draw(self, screen: pygame.Surface):
        if not self.active:
            return

        # render text (wrap if needed)
        padding = 18
        max_w = SCREEN_W - 120
        words = self.text.split(" ")
        lines = []
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if self.font.size(test)[0] > max_w:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)

        txt_surfs = [self.font.render(l, True, self.text_color) for l in lines]
        w = max(s.get_width() for s in txt_surfs) + padding * 2
        h = sum(s.get_height() for s in txt_surfs) + padding * 2

        # extra room for confirm hint (small text at bottom-right)
        hint = None
        if self.confirm_mode:
            hint_text = self.confirm_hint or "(Y/N)"
            hint = self.font.render(hint_text, True, (200, 200, 210))
            # ensure box is wide enough for the hint
            w = max(w, hint.get_width() + padding * 2)
            h += hint.get_height() + 8

        rect = pygame.Rect((SCREEN_W - w) // 2, (SCREEN_H - h) // 2, w, h)

        # shadow
        shadow_rect = rect.move(6, 6)
        pygame.draw.rect(screen, self.shadow, shadow_rect, border_radius=10)
        pygame.draw.rect(screen, self.bg, rect, border_radius=10)
        pygame.draw.rect(screen, self.border, rect, 2, border_radius=10)

        y = rect.y + padding
        for s in txt_surfs:
            screen.blit(s, (rect.x + padding, y))
            y += s.get_height()

        if self.confirm_mode and hint is not None:
            # draw hint in a slightly dimmer color at bottom-right
            screen.blit(hint, (rect.right - padding - hint.get_width(), rect.bottom - padding - hint.get_height()))


ConfirmBox = TextBox


class Game:
    def __init__(self, screen: pygame.Surface, room_json: str = "room1.json"):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)

        self.map = RoomMap("maps", "sprites_en")

        # available rooms (use only those that exist)
        candidates = ["room1.json", "room2.json", "room3.json"]
        self.rooms: List[str] = [r for r in candidates if (Path("maps") / r).exists()]
        if not self.rooms:
            self.rooms = [room_json]

        self.cur = 0
        self.room = self.map.load_json_room(self.rooms[self.cur])
        

        # player at room's spawn
        spawn_x, spawn_y = self.room.get_spawn_point()
        self.player = Player((spawn_x, spawn_y))
        # New: track a door rect the player must leave after declining
        self._door_block_rect: pygame.Rect | None = None
        # Door connection graph: current_room -> { local_door_index: (target_room, target_door_index) }
        self.door_graph: dict[str, dict[int, tuple[str,int]]] = {
            "room2.json": {
                0: ("room1.json", 0),  # top-left door → room1 door 0
                1: ("room5.json", 0),  # bottom-left door → room5 door 0
                2: ("room3.json", 0),  # bottom-right door → room3 door 0
            },
            "room1.json": { 0: ("room2.json", 0) },
            "room5.json": { 0: ("room2.json", 1) },
            # room3 now has a second (bottom-right) door → room4
            "room3.json": {
                0: ("room2.json", 2),
                1: ("room4.json", 0),   # forward to room4
            },
            # room4 door index 1 (right side) → room6
            "room4.json": {
                1: ("room6.json", 0),   # forward to room6
            },
            "room6.json": {
                1: ("room7.json", 0),          # door2 (index1) -> room7 door1(index0 human)
            },
            "room7.json": {
                1: ("room8.json", 1),          # door2 -> room8 door2
                2: ("room11.json", 2),         # door3 -> room11 door3
            },
            "room8.json": {
                0: ("room9.json", 2),          # UPDATED: top-left door -> room9 top-right door
            },
            "room9.json": {
                1: ("room10.json", 0),         # unchanged
                2: ("room8.json", 0),          # NEW explicit reverse: top-right door -> room8 top-left
            },
            "room10.json": {
                0: ("room9.json", 1),
                1: ("room11.json", 0),
            },
            "room11.json": {
                1: ("room12.json", 0),
            },
            "room12.json": {
                # empty; reverse links will populate
            },
        }
        # Auto-add reverse links (door B → door A) if missing
        for src_room, mapping in list(self.door_graph.items()):
            for local_idx, (dst_room, dst_idx) in list(mapping.items()):
                rev_map = self.door_graph.setdefault(dst_room, {})
                if dst_idx not in rev_map:
                    rev_map[dst_idx] = (src_room, local_idx)
        # Ensure mapped rooms exist in self.rooms
        for rn in {n for m in self.door_graph.values() for (n, _) in m.values()}:
            if rn not in self.rooms and (Path("maps") / rn).exists():
                self.rooms.append(rn)
        self.confirm = ConfirmBox(self.font)
        self.previous_room = None  # track only immediate previous room
        self.door_confirm_extra = ""
        self.room_hints: dict[str, str] = {
                "room1.json": "A quiet library. A soft light glows to the north.",
                "room2.json": "Storage room — might be useful items here."
        }
        self.door_confirm_extra = "Tip: collect items before leaving."
        # hazards
        self._hazard_tick_accum = 0.0
        # game over state
        self.game_over = False

    @property
    def offset(self) -> Tuple[int, int]:  # RESTORED
        rw, rh = self.room.pixel_size
        return (SCREEN_W - rw) // 2, (SCREEN_H - rh) // 2

    # ------------ flow ------------
    def _enter_room(self, target_room_name: str, target_door_index: int, source_room: str):
        """Enter target_room_name from source_room.
           Back trip = target_room_name == previous_room → use back_spawn_override if present."""
        if target_room_name not in self.rooms:
            return
        is_back = (self.previous_room is not None and target_room_name == self.previous_room)
        self.cur = self.rooms.index(target_room_name)
        # load room using existing player object so rect is preserved
        self.room = self.map.load_json_room(self.rooms[self.cur], player=self.player)
        self._spawn_after_entry(target_door_index, is_back)

        # Ensure idle state after placement
        if hasattr(self.player, "set_state"):
            self.player.set_state("idle_down")
        else:
            self.player.facing = "down"

        # mark previous room and set door-blocking state
        self.previous_room = source_room
        self._door_block_rect = None
        # Prevent instant door confirm after entering. Track spawn center so
        # we only clear the flag once the player actually moves away.
        self.just_entered_room = True
        self._entry_spawn_center = tuple(self.player.rect.center)

    def _place_player_after_enter(self, is_back: bool, door_index: int):
        # (kept for compatibility but no longer used)
        pass

    def _spawn_at_door_front(self, door_index: int = 0):
        """Place player in front (below) the given door index."""
        if 0 <= door_index < len(self.room.door_cells):
            dx, dy = self.room.door_cells[door_index]
            cx = int((dx + 0.5) * TILE)
            cy_front = int((dy + 1.5) * TILE)
            if cy_front >= self.room.pixel_size[1]:
                cy_front = int((dy + 0.5) * TILE)
            self.player.rect.center = (cx, cy_front)
        else:
            sx, sy = self.room.get_spawn_point()
            self.player.rect.center = (sx, sy)

    def _spawn_at_door_inside(self, door_index: int = 0):
        """Place player just inside (above) the given door index (used on back travel)."""
        if 0 <= door_index < len(self.room.door_cells):
            dx, dy = self.room.door_cells[door_index]
            cx = int((dx + 0.5) * TILE)
            cy_inside = int((dy - 0.5) * TILE)
            if cy_inside < 0:
                cy_inside = int((dy + 0.5) * TILE)
            # Collision safety: if inside a solid, fallback to door center
            test = self.player.rect.copy()
            test.center = (cx, cy_inside)
            for s in self.room.solids:
                if test.colliderect(s):
                    cy_inside = int((dy + 0.5) * TILE)
                    break
            self.player.rect.center = (cx, cy_inside)
        else:
            sx, sy = self.room.get_spawn_point()
            self.player.rect.center = (sx, sy)

    def _spawn_after_entry(self, door_index: int, is_back: bool):
        """Contextual spawn handling for forward/back travel.

        Forward: always spawn in front (below) door.
        Back: if door is at bottom edge -> spawn inside (above) door.
              if door is at top edge -> spawn in front (below) door (so player not outside).
              otherwise fallback to inside placement.
        Also sets a temporary _door_block_rect to avoid instant re-trigger.
        """
        if door_index < 0 or door_index >= len(self.room.door_cells):
            # Fallback to generic spawn
            sx, sy = self.room.get_spawn_point()
            self.player.rect.center = (sx, sy)
            return
        dx, dy = self.room.door_cells[door_index]
        h_tiles = self.room.pixel_size[1] // TILE

        if not is_back:
            self._spawn_at_door_front(door_index)
        else:
            # Place player just outside the door in the direction away from
            # the door surface so they don't spawn overlapping the door.
            door_rect = self.room.door_rects()[door_index]
            pw, ph = self.player.rect.width, self.player.rect.height
            rw, rh = self.room.pixel_size
            placed = False

            # horizontal door (top/bottom)
            if door_rect.width >= door_rect.height:
                if door_rect.centery < rh / 2:
                    # top -> place below
                    px = door_rect.centerx
                    py = door_rect.bottom + ph // 2 + 4
                else:
                    # bottom -> place above
                    px = door_rect.centerx
                    py = door_rect.top - ph // 2 - 4
                self.player.rect.center = (int(px), int(py))
                placed = True
            else:
                # vertical door (left/right)
                if door_rect.centerx < rw / 2:
                    # left -> place to the right
                    px = door_rect.right + pw // 2 + 4
                else:
                    # right -> place to the left
                    px = door_rect.left - pw // 2 - 4
                py = door_rect.centery
                self.player.rect.center = (int(px), int(py))
                placed = True

            # Collision safety: if placed spot intersects solids or wasn't placed,
            # fallback to the room spawn point.
            if placed:
                test = self.player.rect.copy()
                if any(test.colliderect(s) for s in self.room.solids):
                    sx, sy = self.room.get_spawn_point()
                    self.player.rect.center = (sx, sy)
            else:
                sx, sy = self.room.get_spawn_point()
                self.player.rect.center = (sx, sy)

        # After spawning, block re-trigger until player steps away
        door_rect = self.room.door_rects()[door_index]
        self._door_block_rect = door_rect.inflate(-TILE // 4, -TILE // 4)

    def _check_door_trigger(self):
        if self.confirm.active:
            return
        # Prevent confirm dialog immediately after entering room
        if getattr(self, "just_entered_room", False):
            return
        if self._door_block_rect and self.player.rect.colliderect(self._door_block_rect):
            return
        if self._door_block_rect and not self.player.rect.colliderect(self._door_block_rect):
            self._door_block_rect = None
        p = self.player.rect
        cur_name = self.rooms[self.cur]
        links = self.door_graph.get(cur_name, {})
        for idx, d in enumerate(self.room.door_rects()):
            inset = d.inflate(-TILE // 4, -TILE // 4)
            if p.colliderect(inset):
                if idx not in links:
                    continue
                target_room, target_door = links[idx]
                # build message: per-room hint (or global extra) as main text,
                # and a small confirm hint at bottom-right.
                hint_main = self.room_hints.get(cur_name) or self.door_confirm_extra or ""
                if hint_main:
                    msg = hint_main
                else:
                    msg = f"You are at {cur_name}."
                confirm_hint = f"Do you still want to go?"
                self.confirm.show(
                    msg,
                    confirm=True,
                    confirm_hint=confirm_hint,
                    on_yes=lambda tr=target_room, td=target_door, src=cur_name: self._enter_room(tr, td, src),
                    on_no=lambda r=inset: setattr(self, "_door_block_rect", r)
                )
                break

    # ------------ main loop step ------------
    def run_step(self) -> bool:
        """Single frame update/render. Returns False to quit."""
        # Safety: recreate confirm if missing
        if not hasattr(self, "confirm"):
            self.confirm = ConfirmBox(self.font)

        dt = self.clock.tick(FPS) / 1000.0

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if self.game_over:
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._restart()
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_restart_click()
            else:
                self.confirm.handle_event(ev)

        if not self.confirm.active and not self.game_over:
            self.player.update(dt, self.room)
            # If we just entered, only clear the flag once the player has
            # moved away from the spawn center to avoid immediate re-trigger.
            if getattr(self, "just_entered_room", False):
                ex, ey = getattr(self, "_entry_spawn_center", (0, 0))
                px, py = self.player.rect.center
                dx = px - ex
                dy = py - ey
                if dx * dx + dy * dy > 4:  # moved > 2 pixels
                    self.just_entered_room = False
                    self._entry_spawn_center = None
            self._check_door_trigger()
            self._apply_hazard_damage(dt)
            self._check_bomb_trigger()

        self.screen.fill((18, 22, 28))
        off = self.offset
        self.room.draw(self.screen, off)
        self.screen.blit(self.player.image, self.player.rect.move(off))
        self._draw_bomb_effect(off)
        self._draw_health_bar()
        self.confirm.draw(self.screen)
        # delayed game over after death anim
        if hasattr(self, '_death_time') and self._death_time is not None and not self.game_over:
            self._death_time -= dt
            if self._death_time <= 0:
                self._trigger_game_over()
                self._death_time = None
        if self.game_over:
            self._draw_game_over()
        pygame.display.flip()
        return True

    def _start_death_sequence(self, delay: float = 0.6):
        self._death_time = max(0.2, delay)

    # ------------- hazards -------------
    def _apply_hazard_damage(self, dt: float):
        self._hazard_tick_accum += dt
        if self._hazard_tick_accum < HAZARD_TICK_SECONDS:
            return
        self._hazard_tick_accum = 0.0
        for r in self.room.hazard_rects():
            if self.player.hitbox.colliderect(r):
                self.player.take_damage(HAZARD_DAMAGE)
                self.player.hurt_from(r.center)
                if self.player.hp <= 0:
                    self._start_death_sequence()
                break

    def _check_bomb_trigger(self):
        if not hasattr(self.room, 'bomb_rects'):
            return
        for r in self.room.bomb_rects():
            if self.player.hitbox.colliderect(r):
                self._explode_bomb(r.center)
                break

    def _explode_bomb(self, center: tuple[int,int]):
        # load smoke frames if available
        self._bomb_frames = []
        for i in range(0, 10):
            for cand in (f"particles/smoke/{i}.png", f"particles/smoke/{i}.webp"):
                p = Path(cand)
                if p.exists():
                    try:
                        self._bomb_frames.append(pygame.image.load(p.as_posix()).convert_alpha())
                    except Exception:
                        pass
                    break
        self._bomb_center = center
        self._bomb_index = 0
        # instakill with short delay
        self.player.kill_instant()
        self._start_death_sequence()

    def _draw_bomb_effect(self, off: tuple[int,int]):
        if not getattr(self, '_bomb_frames', None):
            return
        if self._bomb_index < len(self._bomb_frames):
            img = self._bomb_frames[self._bomb_index]
            pos = (self._bomb_center[0] + off[0] - img.get_width()//2,
                   self._bomb_center[1] + off[1] - img.get_height()//2)
            self.screen.blit(img, pos)
            self._bomb_index += 1

    # ------------- health bar -------------
    def _draw_health_bar(self):
        max_w = 160
        h = 16
        x, y = 20, 20
        ratio = max(0.0, min(1.0, self.player.hp / max(1, self.player.max_hp)))
        cur_w = int(max_w * ratio)
        pygame.draw.rect(self.screen, (40, 40, 52), pygame.Rect(x-2, y-2, max_w+4, h+4), border_radius=6)
        pygame.draw.rect(self.screen, (210, 50, 60), pygame.Rect(x, y, cur_w, h), border_radius=4)
        pygame.draw.rect(self.screen, (230, 230, 240), pygame.Rect(x, y, max_w, h), 2, border_radius=4)

    # ------------- game over -------------
    def _trigger_game_over(self):
        self.game_over = True

    def _restart(self):
        # reload current room and reset player
        cur_name = self.rooms[self.cur]
        self.player.heal_full()
        self.room = self.map.load_json_room(cur_name, player=self.player)
        self.just_entered_room = False
        self.game_over = False

    def _draw_game_over(self):
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 160))
        self.screen.blit(surf, (0, 0))
        big = pygame.font.Font(None, 56)
        small = self.font
        t1 = big.render("Game Over", True, (255, 230, 230))
        t2 = small.render("Press Enter or Click Play Again", True, (240, 240, 255))
        btn = pygame.Rect(0, 0, 220, 40)
        btn.center = (SCREEN_W//2, SCREEN_H//2 + 60)
        pygame.draw.rect(self.screen, (250, 210, 60), btn, border_radius=8)
        label = self.font.render("Play Again", True, (30, 30, 30))
        self.screen.blit(t1, (SCREEN_W//2 - t1.get_width()//2, SCREEN_H//2 - 80))
        self.screen.blit(t2, (SCREEN_W//2 - t2.get_width()//2, SCREEN_H//2 - 30))
        self.screen.blit(label, (btn.centerx - label.get_width()//2, btn.centery - label.get_height()//2))
        self._restart_btn = btn

    def _handle_restart_click(self):
        pos = pygame.mouse.get_pos()
        if hasattr(self, "_restart_btn") and self._restart_btn.collidepoint(pos):
            self._restart()
