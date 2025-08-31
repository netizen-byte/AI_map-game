import json
from pathlib import Path

map_dir = Path('maps')
rooms = [f'room{i}.json' for i in range(1, 13)]
rooms = [r for r in rooms if (map_dir / r).exists()]

all_refs = []  # list of (room, local_index)
room_doors = {}
for r in rooms:
    p = map_dir / r
    j = json.loads(p.read_text())
    door_layer = None
    for layer in j.get('layers', []):
        if layer.get('name', '').lower() == 'door' or layer.get('type') == 'tilelayer' and layer.get('name','').lower()=='door':
            door_layer = layer
            break
    if door_layer is None:
        # no door layer -> zero doors
        room_doors[r] = []
        continue
    data = door_layer.get('data', [])
    width = door_layer.get('width')
    if not width:
        width = j.get('width')
    door_cells = []
    for idx, val in enumerate(data):
        if val != 0:
            # convert to tile coords
            x = idx % width
            y = idx // width
            door_cells.append((x,y))
    room_doors[r] = door_cells
    for i in range(len(door_cells)):
        all_refs.append((r, i))

# now build circular mapping: each door -> next door in all_refs
# If a room has multiple doors, they get connected into the sequence too.

if not all_refs:
    print('# No doors found in maps; nothing to do')
    raise SystemExit(0)

mapping = {r: {} for r in rooms}
for idx, (r,i) in enumerate(all_refs):
    nxt_room, nxt_i = all_refs[(idx+1) % len(all_refs)]
    mapping[r][i] = (nxt_room, nxt_i)

# print a python literal for game.py
import pprint
pp = pprint.pformat(mapping, width=120)
print('GENERATED_DOOR_GRAPH = ' + pp)
print('\n# Room door counts:')
for r in rooms:
    print(f"{r}: {len(room_doors[r])} doors")
