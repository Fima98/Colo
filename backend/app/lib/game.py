from typing import List, Dict, Tuple
from ..models.player import Player
from .utils import generate_deck
import random

MAX_PLAYERS_PER_GAME = 4


class Game:
    """
    Represents a single game session.
    Manages connected players and broadcast logic.
    """

    def __init__(self, code: str):
        self.code = code              # Unique game identifier
        self.players: List[Player] = []  # List of Player objects in this game

        # Game states
        self.started = False

        # Cards
        self.deck: List[dict] = []
        self.discard_pile: List[dict] = []

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

    def start_game(self):
        self.started = True
        self.deck, hands = generate_deck(len(self.players))

        # Assign cards to players
        player_ids = [p.id for p in self.players]
        self.deck, hands = generate_deck(player_ids)

        for player in self.players:
            player.hand = hands[player.id]

        # Place the first valid card in the discard pile
        first_card = self.deck.pop()
        while first_card.get("value") in ["+4", "rainbow"]:
            self.deck.append(first_card)
            random.shuffle(self.deck)
            first_card = self.deck.pop()

        self.discard_pile.append(first_card)
