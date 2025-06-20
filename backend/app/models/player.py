import uuid
from fastapi import WebSocket
from typing import List


class Player:
    """Represents a player in a game."""

    def __init__(self, name: str, websocket: WebSocket, is_host: bool = False):
        self.name = name
        self.websocket = websocket
        self.id = str(uuid.uuid4())  # Unique ID for the player
        self.is_host = is_host  # True if this player is the host of the game
        self.is_ready = False
        self.hand: List[dict] = []

    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "is_host": self.is_host,
            "is_ready": self.is_ready
        }
