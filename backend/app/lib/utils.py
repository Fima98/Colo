import random
import string

def generate_game_code(k: int = 5) -> str:
    """Generates a random alphanumeric game code of length k."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=k))