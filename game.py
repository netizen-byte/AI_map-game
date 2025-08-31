import random
from pathlib import Path
from typing import List, Tuple

import pygame
from constants import SCREEN_W, SCREEN_H, FPS, TILE, HAZARD_DAMAGE, HAZARD_TICK_SECONDS
from room_map import RoomMap
from player import Player

from UCS import ucs_new

from boss import Boss



class TextBox:
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.active = False
        self.text = ""
        self.confirm_mode = False
        self.on_yes = None
        self.on_no = None
        self.confirm_hint = None
        self.bg = (24,26,30)
        self.border = (110,110,130)
        self.text_color = (235,235,240)
        self.shadow = (6,8,12)

    def show(self, text: str, confirm: bool=False, on_yes=None, on_no=None, confirm_hint: str|None=None):
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
        if not self.active: return
        if ev.type == pygame.KEYDOWN:
            if self.confirm_mode:
                if ev.key in (pygame.K_y, pygame.K_RETURN, pygame.K_e):
                    cb = self.on_yes; self.cancel(); cb and cb()
                elif ev.key in (pygame.K_n, pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    cb = self.on_no; self.cancel(); cb and cb()
            else:
                self.cancel()

    def draw(self, screen: pygame.Surface):
        if not self.active: return
        padding = 18
        max_w = SCREEN_W - 120
        words = self.text.split()
        lines: list[str] = []
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if self.font.size(test)[0] > max_w:
                if line:
                    lines.append(line)
                line = w
            else:
                line = test
        if line: lines.append(line)
        txt_surfs = [self.font.render(l, True, self.text_color) for l in lines]
        w = max(s.get_width() for s in txt_surfs) + padding*2
        h = sum(s.get_height() for s in txt_surfs) + padding*2
        hint = None
        if self.confirm_mode:
            hint = self.font.render(self.confirm_hint or "(Y/N)", True, (200,200,210))
            w = max(w, hint.get_width() + padding*2)
            h += hint.get_height() + 8
        rect = pygame.Rect((SCREEN_W-w)//2, (SCREEN_H-h)//2, w, h)
        shadow = rect.move(6,6)
        pygame.draw.rect(screen, self.shadow, shadow, border_radius=10)
        pygame.draw.rect(screen, self.bg, rect, border_radius=10)
        pygame.draw.rect(screen, self.border, rect, 2, border_radius=10)
        y = rect.y + padding
        for s in txt_surfs:
            screen.blit(s, (rect.x+padding, y)); y += s.get_height()
        if self.confirm_mode and hint:
            screen.blit(hint, (rect.right - padding - hint.get_width(), rect.bottom - padding - hint.get_height()))


ConfirmBox = TextBox


class Game:
    def __init__(self, screen: pygame.Surface, room_json: str="room1.json"):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        
        # Pick 'map' if it exists, else fall back to 'maps'
        map_dir = "map" if (Path("map")/"room1.json").exists() else "maps"
        self.map = RoomMap(map_dir, "sprites_en")

        # Collect all roomN.json present so door_graph targets (like room12) exist
        candidates = [f"room{i}.json" for i in range(1, 21)]
        self.rooms: List[str] = [r for r in candidates if (Path(map_dir)/r).exists()] or ["room1.json"]
        # Ensure canonical ordering: room1 first (start), room12 last (end) if present.
        if "room1.json" in self.rooms:
            self.rooms.remove("room1.json")
            self.rooms.insert(0, "room1.json")
        if "room12.json" in self.rooms:
            # remove any existing occurrence then append to guarantee last position
            try:
                self.rooms.remove("room12.json")
            except ValueError:
                pass
            self.rooms.append("room12.json")
        self.cur = 0
        self.room = self.map.load_json_room(self.rooms[self.cur])
        
        sx, sy = self.room.get_spawn_point()
        self.player = Player((sx, sy))
        self._door_block_rect = None
        # Boss + combat helper state
        self.boss = None
        self._boss_hit_cd = 0.0
        self._boss_death_frames = []
        self._boss_death_index = 0
        self._boss_death_frame_time = 0.0
        self._boss_death_done = False
        self._boss_death_playing = False
        self._boss_death_pos = None

        # Door graph (forward links only; reverse links auto-added below)
        #
    # --- Alternative door_graph examples (fully connected variants) ---
    # Below are five commented, ready-to-use `door_graph` dictionaries. Each one
    # ensures every room and every door index has a destination. To use one,
    # uncomment it and replace the active `self.door_graph` assignment below.
    #
    # Option A - "Complete (preserve original style)"
        self.door_graph_B = {
            "room1.json": {0: ("room6.json", 0)},
            "room2.json": {0: ("room3.json", 0), 2: ("room11.json", 2)},
            "room3.json": {1: ("room4.json", 0)},
            "room4.json": {1: ("room11.json", 1)},
            "room5.json": {0: ("room7.json", 2)},
            "room6.json": {1: ("room9.json", 1)},
            "room7.json": {0: ("room2.json", 1)},
            "room8.json": {0: ("room9.json", 0), 1: ("room7.json", 1)},
            "room9.json": {},
            "room10.json": {0: ("room11.json", 0), 1: ("room12.json", 0)},
            "room11.json": {0: ("room10.json", 0), 1: ("room4.json", 1)},
            "room12.json": {},
        }
        
        self.door_graph_C = {
            "room1.json": {0: ("room3.json", 0)},
            "room2.json": {0: ("room6.json", 1), 1: ("room8.json", 0), 2: ("room4.json", 0)},
            "room3.json": {1: ("room7.json", 2)},
            "room4.json": {1: ("room7.json", 0)},
            "room5.json": {0: ("room7.json", 1)},
            "room6.json": {0: ("room9.json", 1)},
            "room7.json": {},
            "room8.json": {1: ("room11.json", 0)},
            "room9.json": {0: ("room11.json", 1), 1: ("room10.json", 1)},
            "room10.json": {0: ("room11.json", 2), 1: ("room12.json", 0)},
            "room11.json": {},
            "room12.json": {},
        }
        
        self.door_graph_D = {
            "room1.json": {0: ("room9.json", 1)},
            "room2.json": {0: ("room6.json", 0), 1: ("room4.json", 0), 2: ("room3.json", 0)},
            "room3.json": {1: ("room11.json", 1)},
            "room4.json": {1: ("room5.json", 0)},
            "room5.json": {},
            "room6.json": {1: ("room8.json", 1)},
            "room7.json": {0: ("room10.json", 1), 1: ("room11.json", 2), 2: ("room12.json", 0git )},
            "room8.json": {0: ("room9.json", 0)},
            "room9.json": {},
            "room10.json": {1: ("room11.json", 0)},
            "room11.json": {},
            "room12.json": {},
        }
        
        self.door_graph_E = {
            "room1.json": {0: ("room11.json", 0)},
            "room2.json": {0: ("room3.json", 0), 1: ("room4.json", 0), 2: ("room11.json", 2)},
            "room3.json": {1: ("room12.json", 0)},
            "room4.json": {1: ("room7.json", 2)},
            "room5.json": {0: ("room7.json", 0)},
            "room6.json": {0: ("room9.json", 9), 1: ("room8.json", 0)},
            "room7.json": {1: ("room8.json", 1)},
            "room8.json": {},
            "room9.json": {1: ("room10.json", 1)},
            "room10.json": {0: ("room11.json", 1)},
            "room11.json": {},
            "room12.json": {},
        }

        self.door_graph_A = {
            "room1.json": {0: ("room2.json", 0)},
            "room2.json": {1: ("room5.json", 0), 2: ("room3.json", 0)},
            "room3.json": {1: ("room4.json", 0)},
            "room4.json": {1: ("room6.json", 0)},
            "room5.json": {},
            "room6.json": {1: ("room7.json", 0)},
            "room7.json": {1: ("room8.json", 1), 2: ("room11.json", 2)},
            "room8.json": {0: ("room9.json", 0)},
            "room9.json": {1: ("room10.json", 1)},
            "room10.json": {0: ("room11.json", 0)},
            "room11.json": {1: ("room12.json", 0)},
            "room12.json": {},
        }
        # --- Randomly choose one of the prepared door_graph variants at startup ---
        variants = {
            "A": self.door_graph_A,
            "B": self.door_graph_B,
            "C": self.door_graph_C,
            "D": self.door_graph_D,
            "E": self.door_graph_E,
        }
        chosen_key = random.choice(list(variants.keys()))
        self.door_graph = variants[chosen_key]
        print(f"[DoorGraph] Selected variant: {chosen_key}")
        # Auto add reverse links (robust)
        # Ensure every forward mapping has a sensible reverse mapping.
        for src, mapping in list(self.door_graph.items()):
            for local_i, (dst, dst_i) in list(mapping.items()):
                rev = self.door_graph.setdefault(dst, {})
                # Validate the destination room's door count so we don't point at a
                # non-existent index. If the dst room isn't loadable or has no
                # doors, fall back to index 0. Otherwise prefer the declared dst_i
                # if it's in range, else pick a free index in the dst room.
                try:
                    dst_room = self.map.load_json_room(dst)
                    dst_count = len(dst_room.door_cells)
                except Exception:
                    dst_count = 0

                if dst_count <= 0:
                    valid_dst_i = 0
                else:
                    if not isinstance(dst_i, int) or dst_i < 0 or dst_i >= dst_count:
                        # find an unused index in the dst room, otherwise 0
                        used = set(rev.keys())
                        valid_dst_i = next((i for i in range(dst_count) if i not in used), 0)
                    else:
                        valid_dst_i = dst_i

                # Add reverse link without clobbering an existing correct mapping.
                existing = rev.get(valid_dst_i)
                if existing is None:
                    rev[valid_dst_i] = (src, local_i)
                elif existing != (src, local_i):
                    # If the exact reverse already points somewhere else, try to
                    # find a free slot; if none, overwrite the chosen index so at
                    # least one valid reverse exists.
                    if dst_count > 0:
                        placed = False
                        for i in range(dst_count):
                            if i not in rev:
                                rev[i] = (src, local_i)
                                placed = True
                                break
                        if not placed:
                            rev[valid_dst_i] = (src, local_i)

        self._verify_door_graph()
        self._report_unconnected_doors()
        # Ensure all referenced rooms are in self.rooms
        for rn in {n for m in self.door_graph.values() for (n, _) in m.values()}:
            if rn not in self.rooms and (Path(map_dir) / rn).exists():
                self.rooms.append(rn)
        # Re-apply ordering to make sure room1 is at start and room12 is final after any appends.
        if "room1.json" in self.rooms:
            self.rooms.remove("room1.json")
            self.rooms.insert(0, "room1.json")
        if "room12.json" in self.rooms:
            try:
                self.rooms.remove("room12.json")
            except ValueError:
                pass
            self.rooms.append("room12.json")

        # UI + hints
        self.confirm = ConfirmBox(self.font)
        self.previous_room = None
        self.door_confirm_extra = "Tip: collect items before leaving."
        self.room_hints = {
            "room1.json": "A quiet library. A soft light glows to the north.",
            "room2.json": "Storage room — might be useful items here.",
        }

        # ------------- UCS Integration Starts Here -------------
        self.ucs_nodes = {}
        # Pick a trap room but never choose the final boss room (room12.json)
        trap_candidates = [r for r in self.rooms if r != room_json and r != "room12.json"]
        if not trap_candidates:
            trap_candidates = [r for r in self.rooms if r != room_json]
        trap_room = random.choice(trap_candidates) if trap_candidates else None

        for room_name in self.rooms:
            if trap_room is not None and room_name == trap_room:
                danger_cost = 10
                trap = True
            else:
                danger_cost = random.randint(1,5)
                trap = False
            self.ucs_nodes[room_name] = ucs_new.Node(room_name, danger_cost=danger_cost, trap=trap) #create a dict where key is room name and value is Node object
            print(f"this is trap room: {trap_room} with danger cost {danger_cost}") if room_name == trap_room else None
        for src_room_name, mappings in self.door_graph.items():
            if src_room_name in self.ucs_nodes:
                for local_idx, (dst_room_name, _) in mappings.items():
                    if dst_room_name in self.ucs_nodes:
                        self.ucs_nodes[src_room_name].add_door(f"door_{local_idx}", self.ucs_nodes[dst_room_name], cost=1)
        start_node_name = room_json
        # Use room12.json as deterministic goal when available; otherwise fall back
        # to a safe choice among existing rooms (preserves previous behavior only
        # if room12 is not present).
        if "room12.json" in self.rooms:
            goal_node_name = "room12.json"
        # else:
        #     goal_node_name = random.choice([r for r in self.rooms if r != start_node_name]) if len(self.rooms) > 1 else start_node_name
        # print(goal_node_name)
        self.ucs_game = ucs_new.UCSGame(self.ucs_nodes, start_node_name, goal_node_name)
        print(self.ucs_game.get_least_cost_to_goal())
        # print(f"{self.ucs_game.uniform_cost_search(self.ucs_game.start, self.ucs_game.goal)}")
        # ------------- UCS Integration Ends Here -------------

        # Misc gameplay state
        self._hazard_tick_accum = 0.0
        self.game_over = False
        self.show_door_ids = True
        self.win_screen = False


    def display_UCS(self): 
        cur_name = self.rooms[self.cur]
        current_node = self.ucs_nodes.get(cur_name)
        if not current_node:
            return "Pathfinding data not available for this room."

        # Call the UCS algorithm to get the shortest path and cost
        cost, path = self.ucs_game.uniform_cost_search(current_node, self.ucs_game.goal)

        #Also is a shortest path from current node to goal node
        if cost == float("inf"):
            return "There is no path to the goal from here."
        else:
            path_names = [n.name.replace(".json", "") for n in path]
            path_str = "-> ".join(path_names)
            return f"Shortest path is: {path_str}."
        
    def _draw_ucs_path(self): #draw the string from function above to pygame screen
        if not hasattr(self, "ucs_game") or not self.ucs_game:
            return
        
        # Run UCS to get the available path (list of node/room names)
        path = self.display_UCS()  # should return list of room names
        
        if not path:
            return

        small_font = pygame.font.Font(None, 24)
        text = path  # e.g. room1.json → room2.json → room12.json
        surf = small_font.render(text, True, (200, 240, 200))

        # Position at top-right, 20px from edge
        x = SCREEN_W - surf.get_width() - 20
        y = 20  # just under the top edge
        self.screen.blit(surf, (x, y))



    @property
    def offset(self) -> Tuple[int,int]:
        rw, rh = self.room.pixel_size
        return (SCREEN_W - rw)//2, (SCREEN_H - rh)//2

    # ------------- door graph helpers -------------
    def connect_doors(self, room_a: str, idx_a: int, room_b: str, idx_b: int, two_way: bool=True):
        a = self.door_graph.setdefault(room_a, {})
        a[idx_a] = (room_b, idx_b)
        if two_way:
            b = self.door_graph.setdefault(room_b, {})
            b[idx_b] = (room_a, idx_a)
        self._verify_door_graph()

    def _verify_door_graph(self):
        for room, mapping in self.door_graph.items():
            seen = set()
            for li,(dst,dst_i) in mapping.items():
                key = (dst,dst_i)
                if key in seen:
                    print(f"[DoorGraph] WARNING duplicate target {dst}:{dst_i} from {room}")
                else:
                    seen.add(key)

    def _report_unconnected_doors(self):
        """Load each room and report any door indices without a link after reverse fill.
        Exception: room12 bottom door (allowed to be open end)."""
        for room_name in list(self.door_graph.keys()):
            try:
                rm = self.map.load_json_room(room_name)
            except Exception:
                continue
            door_count = len(rm.door_cells)
            if door_count == 0:
                continue
            mapped = set(self.door_graph.get(room_name, {}).keys())
            missing = [i for i in range(door_count) if i not in mapped]
            if not missing:
                continue
            # Allow one unconnected bottom door in room12
            if room_name == "room12.json":
                # Determine bottom door indices (y == max y among doors)
                if len(missing) == 1:
                    max_y = max(y for _,y in rm.door_cells)
                    idx = missing[0]
                    dx, dy = rm.door_cells[idx]
                    if dy == max_y:
                        # allowed
                        continue
                # else fall through and report
            print(f"[DoorGraph] Unconnected doors in {room_name}: {missing} (0-based indices). Provide targets if needed.")

    def debug_list_room_doors(self, room_name: str):
        try:
            tmp = self.map.load_json_room(room_name)
            print(f"[Doors] {room_name} indices:")
            for i,(x,y) in enumerate(tmp.door_cells):
                print(f"  {i}: tile=({x},{y}) pixel=({int((x+0.5)*TILE)},{int((y+0.5)*TILE)})")
        except Exception as e:
            print("[Doors] error", e)

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
        cur_room_name = self.rooms[self.cur]
        cur_room = self.rooms[self.cur]
        if cur_room == "room12.json":
            rw, rh = self.room.pixel_size
            # center of the room
            center_x = rw // 2
            center_y = rh // 2
            self.boss = Boss((center_x, center_y))
        else:
            self.boss = None
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
        """Place player in front of the given door index (inside the room)."""
        if 0 <= door_index < len(self.room.door_cells):
            dx, dy = self.room.door_cells[door_index]
            cx = int((dx + 0.5) * TILE)
            # Check if door is at bottom edge - spawn above it instead of below
            room_height_tiles = self.room.pixel_size[1] // TILE
            if dy >= room_height_tiles - 1:  # Door is at bottom
                cy_front = int((dy - 0.5) * TILE)  # Spawn above door
            else:
                cy_front = int((dy + 1.5) * TILE)  # Spawn below door
            # Safety check
            if cy_front < 0:
                cy_front = int((dy + 0.5) * TILE)
            elif cy_front >= self.room.pixel_size[1]:
                cy_front = int((dy - 0.5) * TILE)
            self.player.rect.center = (cx, cy_front)
            
            # ---------- Check for UCS trap ----------
            # Do not auto-win on entering the UCS goal room; the player must
            # defeat the boss in room12 to finish the game. Instead of instantly
            # flipping to Game Over when a room is marked as a trap, apply damage
            # scaled by the node's danger_cost so the player only dies if HP hits 0.
            if hasattr(self, "ucs_game") and self.ucs_game.nodes.get(self.rooms[self.cur]):
                node = self.ucs_game.nodes[self.rooms[self.cur]]
                if node.trap:
                    # use a modest damage derived from danger_cost so entering a trap
                    # doesn't instantly kill a full-health player. Scale down the
                    # node danger_cost (e.g. divide) and clamp to at least 1.
                    try:
                        damage = max(1, int(node.danger_cost / 4))
                    except Exception:
                        damage = max(1, HAZARD_DAMAGE)

                    # apply damage and show hurt feedback from the door center
                    self.player.take_damage(damage)
                    try:
                        self.player.hurt_from((cx, cy_front))
                    except Exception:
                        # fallback to player's center if door coords missing
                        self.player.hurt_from(self.player.rect.center)
                    # only trigger normal death sequence if hp <= 0 (preserve invuln flow)
                    if self.player.hp <= 0 and not getattr(self.player, "dead", False):
                        if hasattr(self.player, "kill_instant"):
                            self.player.kill_instant()
                        self._start_death_sequence()
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

        Forward: always spawn in front of door.
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
            # For forward travel, spawn in front of the door
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
                    # top door -> place below (inside room)
                    px = door_rect.centerx
                    py = door_rect.bottom + ph // 2 + 4
                else:
                    # bottom door -> place above (inside room)
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
            #
            # Option G - "Path chain (1 -> 2 -> 3 -> 4 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11 -> 12)"
            # - Uses distinct indices so every mapping is reversible (A:i <-> B:j).
            # - Every door index present in the maps is given a destination.
            # - room1 is the start, room12 is the goal and only room12:0 is used.
            # alt_door_graph_G = {
            #     "room1.json": {0: ("room2.json", 0)},
            #     "room2.json": {0: ("room1.json", 0), 1: ("room3.json", 0), 2: ("room5.json", 0)},
            #     "room3.json": {0: ("room2.json", 1), 1: ("room4.json", 0)},
            #     "room4.json": {0: ("room3.json", 1), 1: ("room6.json", 0)},
            #     "room5.json": {0: ("room2.json", 2)},
            #     "room6.json": {0: ("room4.json", 1), 1: ("room7.json", 0)},
            #     "room7.json": {0: ("room6.json", 1), 1: ("room8.json", 0), 2: ("room11.json", 1)},
            #     "room8.json": {0: ("room7.json", 1), 1: ("room9.json", 0)},
            #     "room9.json": {0: ("room8.json", 1), 1: ("room10.json", 0)},
            #     "room10.json": {0: ("room9.json", 1), 1: ("room11.json", 0)},
            #     "room11.json": {0: ("room10.json", 1), 1: ("room7.json", 2), 2: ("room12.json", 0)},
            #     "room12.json": {0: ("room11.json", 2)},
            # }
            #
            # Option H - "Same path as G but alternate leftover pairings"
            # - Keeps the main path (room1->...->room12) but pairs spare doors differently.
            # alt_door_graph_H = {
            #     "room1.json": {0: ("room2.json", 0)},
            #     "room2.json": {0: ("room1.json", 0), 1: ("room3.json", 0), 2: ("room11.json", 1)},
            #     "room3.json": {0: ("room2.json", 1), 1: ("room4.json", 0)},
            #     "room4.json": {0: ("room3.json", 1), 1: ("room6.json", 0)},
            #     "room5.json": {0: ("room7.json", 2)},
            #     "room6.json": {0: ("room4.json", 1), 1: ("room7.json", 0)},
            #     "room7.json": {0: ("room6.json", 1), 1: ("room8.json", 0), 2: ("room5.json", 0)},
            #     "room8.json": {0: ("room7.json", 1), 1: ("room9.json", 0)},
            #     "room9.json": {0: ("room8.json", 1), 1: ("room10.json", 0)},
            #     "room10.json": {0: ("room9.json", 1), 1: ("room11.json", 0)},
            #     "room11.json": {0: ("room10.json", 1), 1: ("room2.json", 2), 2: ("room12.json", 0)},
            #     "room12.json": {0: ("room11.json", 2)},
            # }
            #
            # Option I - "Alternate route (1 -> 2 -> 3 -> 7 -> 11 -> 12) with remaining doors paired"
            # - Another chain that reaches room12 and keeps all links reversible.
            # alt_door_graph_I = {
            #     "room1.json": {0: ("room2.json", 0)},
            #     "room2.json": {0: ("room1.json", 0), 1: ("room3.json", 0), 2: ("room4.json", 0)},
            #     "room3.json": {0: ("room2.json", 1), 1: ("room7.json", 0)},
            #     "room4.json": {0: ("room2.json", 2), 1: ("room5.json", 0)},
            #     "room5.json": {0: ("room4.json", 1)},
            #     "room6.json": {0: ("room6.json", 1), 1: ("room6.json", 0)},
            #     "room7.json": {0: ("room3.json", 1), 1: ("room11.json", 2), 2: ("room8.json", 0)},
            #     "room8.json": {0: ("room7.json", 2), 1: ("room9.json", 0)},
            #     "room9.json": {0: ("room8.json", 1), 1: ("room10.json", 0)},
            #     "room10.json": {0: ("room9.json", 1), 1: ("room11.json", 0)},
            #     "room11.json": {0: ("room10.json", 1), 1: ("room2.json", 2), 2: ("room12.json", 0)},
            #     "room12.json": {0: ("room11.json", 2)},
            # }
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
                # hint_main = self.room_hints.get(cur_name) or self.door_confirm_extra or ""
                hint_main = self.ucs_game.generate_hint(self.ucs_nodes[target_room].danger_cost)

                if hint_main:
                    msg = hint_main
                else:
                    msg = f"You are at {cur_name}."
                confirm_hint = f"Do you still want to go to {target_room.replace('.json', '')}?"
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
        if not hasattr(self, "confirm"):
            self.confirm = ConfirmBox(self.font)

        dt = self.clock.tick(FPS) / 1000.0

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if self.game_over:
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._restart_to_room1()
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_restart_click()
                continue
            else:
                self.confirm.handle_event(ev)

        if not self.confirm.active and not self.game_over:
            self.player.update(dt, self.room)
            # If we just entered, only clear the flag once the player has
            # moved away from the spawn center to avoid immediate re-trigger.
            
            # decrement boss sword hit cooldown
            if self._boss_hit_cd > 0:
                self._boss_hit_cd = max(0.0, self._boss_hit_cd - dt)

            if self.boss and not self.confirm.active and not self.game_over:
                self.boss.update(dt, self.room, self.player)

                # If the boss reduced the player's HP to 0, trigger your normal death flow.
                if self.player.hp <= 0 and not getattr(self.player, "dead", False):
                    # flip to the Die.png animation then show Game Over overlay
                    if hasattr(self.player, "kill_instant"):
                        self.player.kill_instant()
                    self._start_death_sequence(0.8)  # short beat for the death anim
                # trigger death animation start once boss reaches 0
                if self.boss.is_dead() and not self._boss_death_playing:
                    self._start_boss_death_animation()
                    # keep boss object for its final frame reference removal handled by animation
                
            if getattr(self, "just_entered_room", False):
                ex, ey = getattr(self, "_entry_spawn_center", (0, 0))
                px, py = self.player.rect.center
                dx = px - ex
                dy = py - ey
                if dx * dx + dy * dy > 4:  # moved > 2 pixels
                    self.just_entered_room = False
                    self._entry_spawn_center = None
            self._check_door_trigger()
            self._check_bomb_trigger()
            if getattr(self, "_bomb_kill_timer", 0.0) > 0.0:
                self._bomb_kill_timer -= dt
                if self._bomb_kill_timer <= 0.0 and not self.player.dead:
                    self.player.kill_instant()
                    self._start_death_sequence(0.8)
            else:
                self._apply_hazard_damage(dt)

        self.screen.fill((18, 22, 28))
        off = self.offset
        self.room.draw(self.screen, off)
        # >>> draw the boss (was missing)
        if self.boss:
            self.boss.draw(self.screen, off)
            self._draw_boss_hp_bar()

        # boss death animation frames (plays after boss reaches 0 hp)
        if self._boss_death_playing and self._boss_death_frames:
            if self._boss_death_index < len(self._boss_death_frames):
                img = self._boss_death_frames[self._boss_death_index]
                # center at stored death position
                if self._boss_death_pos:
                    x, y = self._boss_death_pos
                else:
                    x, y = self.player.rect.center  # fallback
                r = img.get_rect(center=(x + off[0], y + off[1]))
                self.screen.blit(img, r)
            # advance timing
            self._boss_death_frame_time += dt
            if self._boss_death_frame_time >= 0.07:  # frame duration
                self._boss_death_frame_time = 0.0
                self._boss_death_index += 1
                if self._boss_death_index >= len(self._boss_death_frames):
                    self._boss_death_playing = False
                    self._boss_death_done = True

        # show win screen after death animation completes
        if self._boss_death_done and not self.win_screen:
            self.win_screen = True
            self._boss_death_done = False

        # replace direct sprite blit with player.draw to allow weapon rendering
        if hasattr(self.player, 'draw'):
            self.player.draw(self.screen, off)
            # sword damage check (only if boss alive and player attacking)
            if self.boss and not self.boss.is_dead() and getattr(self.player, 'attacking', False) and self.player.weapon:
                sword_rect = self.player.weapon.rect.copy()
                # boss.hitbox already in room space; weapon rect is in room space (player.draw used offset only during blit)
                if sword_rect.colliderect(self.boss.hitbox) and self._boss_hit_cd <= 0.0:
                    # reduced sword damage (single small hit with cooldown)
                    self.boss.take_damage(10)  # adjust value if further reduction needed
                    self._boss_hit_cd = 0.35  # cannot damage again for 0.35s
        else:
            self.screen.blit(self.player.image, self.player.rect.move(off))

        if self.show_door_ids:
            self._draw_door_id_overlay(off)
        self._draw_bomb_effect(off)
        self._draw_health_bar()

        #draw UCS
        self._draw_ucs_path()  # now shows top-right
        self._draw_current_room_name()

        self.confirm.draw(self.screen)
        # delayed game over after death anim
        if hasattr(self, '_death_time') and self._death_time is not None and not self.game_over:
            self._death_time -= dt
            if self._death_time <= 0:
                self._trigger_game_over()
                self._death_time = None
        if self.game_over:
            self._draw_game_over()
        if self.win_screen:
            self._draw_win_screen()
        pygame.display.flip()
        return True

    def _start_death_sequence(self, delay: float = 0.6):
        self._death_time = max(0.2, delay)

    # ------------- hazards -------------
    def _apply_hazard_damage(self, dt: float):
        if getattr(self, "_bomb_kill_timer", 0.0) > 0.0:
            return
        self._hazard_tick_accum += dt
        if self._hazard_tick_accum < HAZARD_TICK_SECONDS:
            return
        self._hazard_tick_accum = 0.0
        for r in self.room.hazard_rects():
            if self.player.hitbox.colliderect(r):
                self.player.take_damage(HAZARD_DAMAGE)
                self.player.hurt_from(r.center)
                if self.player.hp <= 0 and not self.player.dead:
                    if hasattr(self.player, "kill_instant"):
                        self.player.kill_instant()
                    self._start_death_sequence()
                break

    def _check_bomb_trigger(self):
        if getattr(self, "_bomb_kill_timer", 0.0) > 0.0:
            return
        if not hasattr(self.room, "bomb_rects"):
            return
        for r in self.room.bomb_rects():
            if self.player.hitbox.colliderect(r):
                self._explode_bomb(r.center)
                break

    def _explode_bomb(self, center: tuple[int, int]):
        self._bomb_frames = []
        smoke_dir = Path("particles/smoke")
        if smoke_dir.exists():
            for p in sorted(smoke_dir.iterdir()):
                if p.suffix.lower() in (".png"):
                    try:
                        self._bomb_frames.append(pygame.image.load(p.as_posix()).convert_alpha())
                    except Exception:
                        pass
        self._bomb_center = center
        self._bomb_index = 0
        self.player.hurt_from(center, duration=0.18)
        self._bomb_kill_timer = 0.22


    def _draw_bomb_effect(self, off: tuple[int,int]):
        if not getattr(self, '_bomb_frames', None):
            return
        if self._bomb_index < len(self._bomb_frames):
            img = self._bomb_frames[self._bomb_index]
            pos = (self._bomb_center[0] + off[0] - img.get_width()//2,
                   self._bomb_center[1] + off[1] - img.get_height()//2)
            self.screen.blit(img, pos)
            self._bomb_index += 1
    
    def _draw_current_room_name(self):
        # small font for overlay
        small_font = pygame.font.Font(None, 24)
        cur_room_name = self.rooms[self.cur].replace(".json", "")  # remove .json if you want
        text_surf = small_font.render(f"Room: {cur_room_name}", True, (255, 255, 200))
        
        # bottom-left position with 20px padding
        x = 20
        y = SCREEN_H - text_surf.get_height() - 20
        self.screen.blit(text_surf, (x, y))

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

    def _draw_boss_hp_bar(self):
        if not self.boss or self.boss.is_dead():
            return
        max_w = 300
        h = 18
        x = (SCREEN_W - max_w)//2
        y = 60
        ratio = max(0.0, min(1.0, self.boss.hp / max(1, self.boss.max_hp)))
        cur_w = int(max_w * ratio)
        pygame.draw.rect(self.screen, (30,30,40), pygame.Rect(x-2,y-2,max_w+4,h+4), border_radius=8)
        pygame.draw.rect(self.screen, (200,40,50), pygame.Rect(x,y,cur_w,h), border_radius=6)
        pygame.draw.rect(self.screen, (240,240,255), pygame.Rect(x,y,max_w,h), 2, border_radius=6)

    def _start_boss_death_animation(self):
        """Load raccoon particle death frames and start playback."""
        self._boss_death_frames.clear()
        base = Path("particles")/"raccoon"
        bw = bh = 0
        if self.boss:
            bw, bh = self.boss.rect.size
        if base.exists():
            for p in sorted(base.iterdir(), key=lambda q: q.name):
                if p.suffix.lower() not in (".png", ".webp"): continue
                try:
                    img = pygame.image.load(p.as_posix()).convert_alpha()
                    # scale to boss size if we have it
                    if bw and bh:
                        img = pygame.transform.smoothscale(img, (bw, bh))
                    self._boss_death_frames.append(img)
                except Exception:
                    pass
        if not self._boss_death_frames:
            # simple fallback effect
            surf = pygame.Surface((64,64), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255,200,60,180), (32,32), 30)
            pygame.draw.circle(surf, (255,80,40,220), (32,32), 18)
            if bw and bh:
                surf = pygame.transform.smoothscale(surf, (bw, bh))
            self._boss_death_frames = [surf]*10
        # store position (center of boss rect) before removing boss reference for drawing
        if self.boss:
            self._boss_death_pos = self.boss.rect.center
        self._boss_death_index = 0
        self._boss_death_frame_time = 0.0
        self._boss_death_playing = True
        # remove boss entity from world (so no more collisions / hp bar) but keep animation
        self.boss = None

    def _draw_win_screen(self):
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        surf.fill((0,0,0,160))
        self.screen.blit(surf, (0,0))
        big = pygame.font.Font(None, 60)
        mid = pygame.font.Font(None, 36)
        small = self.font
        title = big.render("Victory!", True, (255, 240, 120))
        msg = mid.render("You defeated the Boss", True, (245,245,250))
        hint = small.render("Press Enter to play again", True, (230,230,235))
        self.screen.blit(title, (SCREEN_W//2 - title.get_width()//2, SCREEN_H//2 - 120))
        self.screen.blit(msg, (SCREEN_W//2 - msg.get_width()//2, SCREEN_H//2 - 60))
        self.screen.blit(hint, (SCREEN_W//2 - hint.get_width()//2, SCREEN_H//2))

    # ------------- game over -------------
    def _trigger_game_over(self):
        self.game_over = True

    def _restart(self):
        cur_name = self.rooms[self.cur]
        try:
            self.player.dead = False
            self.player.invuln_timer = 0.0
            self.player.hurt_timer = 0.0
            self.player.vel.update(0, 0)
        except Exception:
            pass
        self.player.heal_full()
        self._hazard_tick_accum = 0.0
        if hasattr(self, "_death_time"):
            self._death_time = None
        if hasattr(self, "_bomb_frames"):
            self._bomb_frames = []
            self._bomb_index = 0
        self.room = self.map.load_json_room(cur_name, player=self.player)
        self.just_entered_room = False
        self.game_over = False
        if hasattr(self, "confirm"):
            self.confirm.cancel()
        if hasattr(self, "_restart_btn"):
            delattr(self, "_restart_btn")

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
            self._restart_to_room1()

    # ------------- debug overlays -------------
    def _draw_door_id_overlay(self, off: tuple[int,int]):
        try:
            small = pygame.font.Font(None, 20)
            for i, r in enumerate(self.room.door_rects()):
                tag = small.render(str(i), True, (255, 255, 0))
                dr = r.move(off)
                pygame.draw.rect(self.screen, (255, 255, 0), dr, 1)
                self.screen.blit(tag, (dr.x + 2, dr.y + 2))
        except Exception:
            pass
            self._restart_to_room1()

    def _restart_to_room1(self):
        try:
            pygame.event.clear()
        except Exception:
            pass
        self.__init__(self.screen, room_json="room1.json")


pygame.mixer.init()
pygame.mixer.music.load('audio/main.ogg')  # path to your main theme
pygame.mixer.music.set_volume(0.5)   # optional volume adjustment
pygame.mixer.music.play(-1, 0.0)     # -1 means loop indefinitely, start at 0.0s
