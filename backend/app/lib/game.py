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

        # Game order management
        self.order: 'GameOrder' = None  # Will be initialized when the game starts

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

        # Shuffle the player order
        random.shuffle(self.players)

        # Initialize the game order
        self.order = GameOrder(self.players)


class GameOrder:
    class OrderNode:
        def __init__(self, player: Player):
            self.player = player
            self.next: 'GameOrder.OrderNode' = None
            self.prev: 'GameOrder.OrderNode' = None

    def __init__(self, players: List[Player]):
        if len(players) != 4:
            raise ValueError("GameOrder requires exactly 4 players.")

        # Create nodes
        self.nodes = [self.OrderNode(p) for p in players]

        # Link them in a circular doubly linked list
        for i in range(4):
            self.nodes[i].next = self.nodes[(i + 1) % 4]
            self.nodes[i].prev = self.nodes[(i - 1) % 4]

        self.current = self.nodes[0]  # Starting player
        self.reversed = False         # Play direction

    def get_current_player(self) -> Player:
        return self.current.player

    def next_turn(self):
        """
        Move to the next player based on direction.
        """
        self.current = self.current.prev if self.reversed else self.current.next

    def reverse(self):
        """
        Reverse the order of turns.
        """
        self.reversed = not self.reversed

    def to_list(self) -> List[str]:
        """
        Return the list of player names in current order for debugging.
        """
        result = []
        node = self.current
        for _ in range(4):
            result.append(node.player.name)
            node = node.prev if self.reversed else node.next
        return result
