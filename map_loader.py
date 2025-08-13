# map_loader.py
# Stub for future Tiled integration (TMX/JSON)
# Keep here so imports won't break when you wire it in later.

class MapLoader:
    def __init__(self, maps_path="maps"):
        self.maps_path = maps_path

    def load(self, name):
        raise NotImplementedError("Tiled/JSON loader not implemented in this minimal build.")
