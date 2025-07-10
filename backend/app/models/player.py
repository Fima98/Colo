import uuid
from typing import List, Dict
from fastapi import WebSocket


class Player:
    """Represents a single player in a game."""

    def __init__(self, name: str, websocket: WebSocket, is_host: bool = False):
        self.id = str(uuid.uuid4())
        self.name = name
        self.websocket = websocket
        self.is_host = is_host
        self.is_ready = False
        self.hand: List[Dict] = []

    def to_dict(self) -> dict:
        """Returns a serializable dictionary representation of the player."""
        return {
            "id": self.id,
            "name": self.name,
            "is_host": self.is_host,
            "is_ready": self.is_ready,
            "card_count": len(self.hand)
        }

    async def send_error(self, message: str):
        """Sends a standardized error message to this player."""
        await self.websocket.send_json({"status": "error", "message": message})
