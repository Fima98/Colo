import random
import string
from typing import List, Dict, Tuple


def generate_game_code(k: int = 5) -> str:
    """Generates a random alphanumeric game code of length k."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=k))


def generate_deck(player_ids: List[str]) -> Tuple[List[dict], Dict[str, List[dict]]]:
    colors = ["pink", "orange", "lime", "blue"]
    numbers = [str(n) for n in range(10)]  # '0' to '9'
    color_actions = ["block", "+2", "reverse"]
    colorless_actions = ["+4", "rainbow"]

    deck: List[dict] = []

    # Colored number cards (0–9) and action cards
    for color in colors:
        for num in numbers:
            deck.append({"color": color, "value": num})
            deck.append({"color": color, "value": num})  # по 2 кожної

        for action in color_actions:
            deck.append({"color": color, "value": action})
            deck.append({"color": color, "value": action})

    # Colorless action cards
    for action in colorless_actions:
        for _ in range(4):
            deck.append({"value": action})  # без 'color'

    # Shuffle the deck
    random.shuffle(deck)

    # Deal 6 cards to each player
    hands: Dict[str, List[dict]] = {}
    for player_id in player_ids:
        hands[player_id] = [deck.pop() for _ in range(6)]

    return deck, hands
