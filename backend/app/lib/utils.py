import random
import string
from typing import Dict, List, Tuple


def generate_game_code(k: int = 5) -> str:
    """Generates a random, uppercase, alphanumeric game code."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=k))


def generate_deck(player_ids: List[str]) -> Tuple[List[Dict], Dict[str, List[Dict]]]:
    """Creates a shuffled deck of cards and deals them to players."""
    colors = ["pink", "orange", "lime", "blue"]
    color_actions = ["block", "+2", "reverse"]
    wild_actions = ["+4", "rainbow"]

    deck: List[Dict] = []

    # Create colored cards
    for color in colors:
        # One '0' card per color
        deck.append({"color": color, "value": "0"})
        # Two of every other number (1-9)
        for num in range(1, 10):
            deck.append({"color": color, "value": str(num)})
            deck.append({"color": color, "value": str(num)})
        # Two of each action card
        for action in color_actions:
            deck.append({"color": color, "value": action})
            deck.append({"color": color, "value": action})

    # Create wild cards
    for action in wild_actions:
        for _ in range(4):
            # Wild cards have no color initially
            deck.append({"color": None, "value": action})

    random.shuffle(deck)

    # Deal 7 cards to each player
    hands: Dict[str, List[Dict]] = {player_id: [] for player_id in player_ids}
    for _ in range(7):
        for player_id in player_ids:
            if deck:
                hands[player_id].append(deck.pop())

    return deck, hands
