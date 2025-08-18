import random
from pathlib import Path
from typing import List, Tuple, Optional

import pygame
from constants import SCREEN_W, SCREEN_H, FPS, TILE
from room_map import RoomMap
from player import Player


class ConfirmBox:
    """Simple Y/N modal."""
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.active = False
        self.text = ""
        self.on_yes = None
        self.on_no = None

    def show(self, text: str, on_yes, on_no=None):
        self.active = True
        self.text = text
        self.on_yes = on_yes
        self.on_no = on_no

    def cancel(self):
        self.active = False
        self.text = ""
        self.on_yes = None
        self.on_no = None

    def handle_event(self, ev: pygame.event.Event):
        if not self.active:
            return
        if ev.type == pygame.KEYDOWN:
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

    def draw(self, screen: pygame.Surface):
        if not self.active:
            return
        # panel
        txt = self.font.render(self.text + "  (Y/N)", True, (230, 230, 230))
        padding = 16
        w, h = txt.get_width() + padding * 2, txt.get_height() + padding * 2
        rect = pygame.Rect((SCREEN_W - w) // 2, (SCREEN_H - h) // 2, w, h)
        pygame.draw.rect(screen, (20, 20, 24), rect)
        pygame.draw.rect(screen, (120, 120, 140), rect, 2)
        screen.blit(txt, (rect.x + padding, rect.y + padding))


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
        self.previous_room: str | None = None  # track only immediate previous room

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
        self.room = self.map.load_json_room(self.rooms[self.cur], player=self.player)

        if is_back and self.room.back_spawn_override:
            self.player.rect.center = self.room.get_spawn_point(prefer_back=True)
            if hasattr(self.player, "set_state"):
                self.player.set_state("idle_down")
            else:
                self.player.facing = "down"
        else:
            self._spawn_at_door_front(target_door_index)

        self.previous_room = source_room
        self._door_block_rect = None

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
        if hasattr(self.player, "set_state"):
            self.player.set_state("idle_down")
        else:
            self.player.facing = "down"

    def _check_door_trigger(self):
        if self.confirm.active:
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
                self.confirm.show(
                    f"Go to {target_room}?",
                    on_yes=lambda tr=target_room, td=target_door, src=cur_name: self._enter_room(tr, td, src),
                    on_no=lambda r=inset: setattr(self, "_door_block_rect", r)
                )
                break

    # ------------ main loop step ------------
    def run_step(self) -> bool:
        # Safety: recreate confirm if missing (prevents AttributeError if __init__ was interrupted)
        if not hasattr(self, "confirm"):
            self.confirm = ConfirmBox(self.font)

        dt = self.clock.tick(FPS) / 1000.0

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            self.confirm.handle_event(ev)

        # update only when not in modal
        if not self.confirm.active:
            self.player.update(dt, self.room)
            self._check_door_trigger()

        # draw
        self.screen.fill((18, 22, 28))
        off = self.offset
        self.room.draw(self.screen, off)
        self.screen.blit(self.player.image, self.player.rect.move(off))
        self.confirm.draw(self.screen)

        pygame.display.flip()
        return True
        pygame.display.flip()
        return True
        return True
        return True
        return True
