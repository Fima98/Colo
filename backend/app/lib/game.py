import random
from typing import Dict, List, Optional
import asyncio

from ..models.player import Player
from .utils import generate_deck

MAX_PLAYERS_PER_GAME = 4


class Game:
    """Manages the state and logic of a single game session."""

    def __init__(self, code: str):
        self.code = code
        self.players: List[Player] = []

        self.started = False

        self.deck: List[Dict] = []
        self.discard_pile: List[Dict] = []

        self.order: 'GameOrder' = None

        self.colo_pending: Optional[Player] = None
        self.colo_task: Optional[asyncio.Task] = None

    async def broadcast(self, message: dict):
        """Sends a message to all connected players in the game."""
        disconnected_players = []
        for player in self.players:
            try:
                await player.websocket.send_json(message)
            except Exception:
                disconnected_players.append(player)

        for player in disconnected_players:
            self.remove_player(player)

    def add_player(self, player: Player):
        if not self.is_full():
            self.players.append(player)

    def remove_player(self, player: Player):
        self.players = [p for p in self.players if p.id != player.id]

    def is_full(self) -> bool:
        return len(self.players) >= MAX_PLAYERS_PER_GAME

    def to_dict_list(self) -> List[dict]:
        return [p.to_dict() for p in self.players]

    def _reshuffle_discard_pile(self):
        """Reshuffles the discard pile back into the deck, leaving the top card."""
        if not self.discard_pile:
            return
        top_card = self.discard_pile.pop()
        self.deck.extend(self.discard_pile)
        random.shuffle(self.deck)
        self.discard_pile = [top_card]
        print("Reshuffled discard pile into deck.")

    async def start_game(self):
        """Initializes the game state, deals cards, and notifies players."""
        self.started = True
        player_ids = [p.id for p in self.players]
        self.deck, hands = generate_deck(player_ids)

        for player in self.players:
            player.hand = hands.get(player.id, [])

        # Ensure the first card is not a wild card
        first_card = self.deck.pop()
        while first_card['value'] in ["+4", "rainbow"]:
            self.deck.append(first_card)
            random.shuffle(self.deck)
            first_card = self.deck.pop()

        self.discard_pile.append(first_card)

        random.shuffle(self.players)
        self.order = GameOrder(self.players)

        current_turn_player_id = self.order.get_current_player().id

        for player in self.players:
            await player.websocket.send_json({
                "status": "game_started",
                "your_hand": player.hand,
                "top_card": self.discard_pile[-1],
                "player_hands": {p.id: len(p.hand) for p in self.players},
                "turn_order": [p.id for p in self.order.get_player_sequence()],
                "current_turn": current_turn_player_id
            })

    async def process_move(self, player: Player, move: dict):
        """Validates and processes a player's move."""
        card_to_play = move.get("card")
        if not card_to_play:
            return await player.send_error("Invalid move format.")

        if card_to_play not in player.hand:
            return await player.send_error("You don't have that card.")

        top_card = self.discard_pile[-1]
        is_wild = card_to_play['value'] in ['+4', 'rainbow']

        if not (card_to_play['color'] == top_card['color'] or card_to_play['value'] == top_card['value'] or is_wild):
            return await player.send_error("Invalid card played.")

        player.hand.remove(card_to_play)

        if is_wild:
            new_color = move.get("new_color")
            if new_color not in ["pink", "orange", "lime", "blue"]:
                player.hand.append(card_to_play)  # Return card to hand
                return await player.send_error("A new color must be chosen for a wild card.")
            card_to_play['color'] = new_color

        self.discard_pile.append(card_to_play)

        await self._handle_action_cards(card_to_play)

        if card_to_play['value'] not in ['block', 'reverse']:
            self.order.next_turn()

        await self.broadcast({
            "status": "move_made",
            "player_id": player.id,
            "card": card_to_play,
            "player_hands": {p.id: len(p.hand) for p in self.players},
            "top_card": self.discard_pile[-1],
            "current_turn": self.order.get_current_player().id
        })

        if not player.hand:
            await self.broadcast({"status": "game_over", "winner_id": player.id})
            self.started = False  # End game

    async def _handle_action_cards(self, card: dict):
        """Applies the effects of special action cards like +2, +4, block, or reverse."""
        value = card['value']

        if value == "+2":
            await self.draw_cards_for_next_player(2)
        elif value == "+4":
            await self.draw_cards_for_next_player(4)
        elif value == "block":
            self.order.next_turn()  # Skips the next player
        elif value == "reverse":
            self.order.reverse()

    async def draw_cards_for_next_player(self, count: int):
        """Forces the next player in order to draw a specified number of cards."""
        target_player = self.order.get_next_player()
        drawn_cards = []
        for _ in range(count):
            if not self.deck:
                self._reshuffle_discard_pile()
            if self.deck:  # Check again in case reshuffle yielded nothing
                drawn_card = self.deck.pop()
                target_player.hand.append(drawn_card)
                drawn_cards.append(drawn_card)

        if drawn_cards:
            # Notify the targeted player of their new hand
            await target_player.websocket.send_json({
                "status": "cards_drawn_for_you",
                "new_cards": drawn_cards,
                "your_hand": target_player.hand
            })

    async def draw_card(self, player: Player):
        """Allows the current player to draw one card from the deck."""
        if not self.deck:
            self._reshuffle_discard_pile()

        if not self.deck:
            return await player.send_error("The deck is empty.")

        card = self.deck.pop()
        player.hand.append(card)

        # Notify the player of their new card
        await player.websocket.send_json({
            "status": "card_drawn",
            "new_card": card,
            "your_hand": player.hand
        })

        # Notify all players of the hand count change
        await self.broadcast({
            "status": "hand_updated",
            "player_id": player.id,
            "new_count": len(player.hand)
        })

    async def start_colo_challenge(self, player: Player, broadcast_callback):
        """
        Called when a player has one card left to initiate the 'COLO' challenge.
        """
        if self.colo_task:  # Cancel any existing challenge
            self.colo_task.cancel()

        self.colo_pending = player
        await broadcast_callback({
            "status": "colo_started",
            "target_player_id": player.id,
        })

        self.colo_task = asyncio.create_task(
            self._colo_timeout(broadcast_callback))

    async def _colo_timeout(self, broadcast_callback):
        try:
            await asyncio.sleep(5)  # 5 seconds to press "COLO"
            # Timeout occurred, no one pressed
            self.colo_pending = None
            self.colo_task = None
            await broadcast_callback({
                "status": "colo_timeout"
            })
        except asyncio.CancelledError:
            pass

    async def colo_pressed(self, player: Player, broadcast_callback):
        """
        Called when a player presses the 'COLO' button.
        If another player catches the one with 1 card — penalty applies.
        """
        if self.colo_pending is None:
            await player.websocket.send_json({
                "status": "colo_invalid_press",
                "message": "There is no COLO challenge right now."
            })
            return

        target = self.colo_pending

        if player.id == target.id:
            # The player with 1 card pressed COLO — success!
            await player.websocket.send_json({
                "status": "colo_success",
                "message": "You successfully called COLO!"
            })
        else:
            # Someone else pressed COLO first — target player gets 2 penalty cards
            penalty_cards = []
            for _ in range(2):
                if not self.deck:
                    self._reshuffle_discard_pile()
                if self.deck:
                    card = self.deck.pop()
                    target.hand.append(card)
                    penalty_cards.append(card)

            await target.websocket.send_json({
                "status": "colo_penalty",
                "message": "Another player called COLO before you!",
                "new_cards": penalty_cards,
                "your_hand": target.hand
            })

            await broadcast_callback({
                "status": "colo_failed",
                "target_id": target.id,
                "by_id": player.id
            })

        # Reset challenge in all cases
        if self.colo_task:
            self.colo_task.cancel()
        self.colo_task = None
        self.colo_pending = None


class GameOrder:
    """Manages the turn order of players in a circular fashion."""
    class OrderNode:
        def __init__(self, player: Player):
            self.player = player
            self.next: 'GameOrder.OrderNode' = None
            self.prev: 'GameOrder.OrderNode' = None

    def __init__(self, players: List[Player]):
        if not players:
            raise ValueError("Cannot create a game order with no players.")

        self.nodes = [self.OrderNode(p) for p in players]
        num_players = len(self.nodes)

        for i in range(num_players):
            self.nodes[i].next = self.nodes[(i + 1) % num_players]
            self.nodes[i].prev = self.nodes[(
                i - 1 + num_players) % num_players]

        self.current = self.nodes[0]
        self.reversed = False

    def get_current_player(self) -> Player:
        return self.current.player

    def get_next_player(self) -> Player:
        """Gets the next player without advancing the turn."""
        return self.current.prev.player if self.reversed else self.current.next.player

    def next_turn(self):
        self.current = self.current.prev if self.reversed else self.current.next

    def reverse(self):
        self.reversed = not self.reversed

    def get_player_sequence(self) -> List[Player]:
        """Returns the players in the current turn order."""
        sequence = []
        node = self.current
        for _ in range(len(self.nodes)):
            sequence.append(node.player)
            node = node.next
        return sequence
