from typing import List
import asyncio
from .utils import generate_game_code
from ..models.player import Player
from fastapi import WebSocket

MAX_PLAYERS_PER_GAME = 4


class Game:
    """
    Represents a single game session.
    Manages connected players and broadcast logic.
    """

    def __init__(self, code: str):
        self.code = code              # Unique game identifier
        self.players: List[Player] = []  # List of Player objects in this game

    async def broadcast(self, message: dict):
        """
        Send a JSON message to all connected players.
        Automatically removes players whose connections fail.
        """
        connected: List[Player] = []
        for p in self.players:
            try:
                await p.websocket.send_json(message)
                connected.append(p)
            except Exception as e:
                # If sending fails, assume the player disconnected
                print(f"Failed to send to {p.name}: {e}")
        # Update the player list, keeping only successful connections
        self.players = connected

    def add_player(self, player: Player) -> None:
        """
        Add a new player to the game.
        """
        self.players.append(player)

    def remove_player(self, player: Player) -> None:
        """
        Remove a player (by ID) from the game.
        """
        self.players = [p for p in self.players if p.id != player.id]

    def is_full(self) -> bool:
        """
        Check if the game has reached maximum capacity.
        """
        return len(self.players) >= MAX_PLAYERS_PER_GAME

    def to_dict_list(self) -> List[dict]:
        """
        Get a serializable list of player info dicts.
        """
        return [p.to_dict() for p in self.players]
