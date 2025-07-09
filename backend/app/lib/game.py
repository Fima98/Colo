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

    async def process_move(self, player: Player, move: dict):
        """
        Process a move made by a player.
        Supports playing multiple cards of the same value, including action cards.

        move = {
            "cards": List[{"color": str, "value": str}],
            # for wild cards: "new_color": str
        }
        """
        cards = move.get("cards")
        if not cards or not isinstance(cards, list):
            await player.websocket.send_json({
                "status": "error",
                "message": "Move must include a list of 'cards'."
            })
            return

        # Check all cards have the same value
        first_value = cards[0]["value"]
        if any(c["value"] != first_value for c in cards):
            await player.websocket.send_json({
                "status": "error",
                "message": "All cards played in a turn must have the same value."
            })
            return

        # Check player owns all cards
        for card in cards:
            if card not in player.hand:
                await player.websocket.send_json({
                    "status": "error",
                    "message": "You cannot play a card you don't have."
                })
                return

        top = self.discard_pile[-1]
        color_matches = cards[0]["color"] == top["color"]
        value_matches = cards[0]["value"] == top["value"]
        is_wild = cards[0]["value"] in ["rainbow", "+4"]

        if not (color_matches or value_matches or is_wild):
            await player.websocket.send_json({
                "status": "error",
                "message": "Invalid card played."
            })
            return

        # Remove cards from player's hand and place on discard pile
        for card in cards:
            player.hand.remove(card)
            self.discard_pile.append(card)

        # Handle wild cards
        if first_value in ["rainbow", "+4"]:
            new_color = move.get("new_color")
            if new_color not in ["red", "yellow", "green", "blue"]:
                await player.websocket.send_json({
                    "status": "error",
                    "message": "You must specify a valid new_color for wild cards."
                })
                for card in cards:
                    player.hand.append(card)
                    self.discard_pile.pop()
                return
            cards[-1]["color"] = new_color  # Only final card sets color

        current_idx = self.order.nodes.index(
            next(n for n in self.order.nodes if n.player.id == player.id)
        )

        def next_idx(steps=1):
            idx = current_idx
            for _ in range(steps):
                idx = (idx - 1) if self.order.reversed else (idx + 1)
                idx %= len(self.order.nodes)
            return idx

        # Handle action cards stacking
        if first_value == "+2":
            total_draw = 2 * len(cards)
            target = self.order.nodes[next_idx()].player
            for _ in range(total_draw):
                if self.deck:
                    target.hand.append(self.deck.pop())
        elif first_value == "+4":
            total_draw = 4 * len(cards)
            target = self.order.nodes[next_idx()].player
            for _ in range(total_draw):
                if self.deck:
                    target.hand.append(self.deck.pop())
        elif first_value == "block":
            self.order.current = self.order.nodes[next_idx(
                steps=1 + len(cards))]
        elif first_value == "reverse":
            for _ in range(len(cards)):
                self.order.reverse()
            if len(self.players) == 2 and len(cards) % 2 == 1:
                self.order.current = self.order.nodes[next_idx()]

        # Move to next turn if not a skip or forced advance
        if first_value not in ["block", "reverse"]:
            self.order.next_turn()

        # Broadcast updated game state to all players
        await self.broadcast({
            "status": "move_accepted",
            "player_id": player.id,
            "cards": cards,
            "hands": {p.id: len(p.hand) for p in self.players},
            "next_player": self.order.get_current_player().id
        })


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
