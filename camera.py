# camera.py
class Camera:
    """Simple room-locked camera. (We draw rooms at 0,0 and 'snap' the camera there.)"""
    def __init__(self):
        self.x = 0
        self.y = 0

    def snap_to(self, room_px_x: int, room_px_y: int):
        self.x = room_px_x
        self.y = room_px_y
