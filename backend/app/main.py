from typing import Optional, Dict, List, Union
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Import a utility to generate unique game codes
from .lib.utils import generate_game_code
# Import the Player model (holds name, websocket connection, etc.)
from .models.player import Player
from .lib.game import Game, MAX_PLAYERS_PER_GAME

app = FastAPI()

# Enable CORS to allow clients from any origin to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow requests from all domains
    allow_methods=["*"],       # Allow all HTTP methods
    allow_headers=["*"],       # Allow all headers
)

# In-memory store mapping game codes to Game instances
games: Dict[str, "Game"] = {}


@app.post("/create")
def create_game_http():
    """
    HTTP endpoint to create a new game.
    Generates a unique code and initializes a Game instance.
    """
    code = generate_game_code()
    # Ensure code uniqueness
    while code in games:
        code = generate_game_code()
    games[code] = Game(code)
    print(f"New game created: {code}")
    return {"success": True, "code": code}


@app.get("/check_code/{code}")
async def check_code(code: str):
    """
    HTTP endpoint to verify if a game code exists and is not full.
    Returns JSON with 'exists' and 'full' booleans.
    """
    if code in games:
        return {"exists": True, "full": games[code].is_full()}
    return {"exists": False, "full": False}


@app.websocket("/ws/game/{code}")
async def game_ws(websocket: WebSocket, code: str):
    """
    WebSocket endpoint for joining a game.
    1. Accepts the connection.
    2. Validates the game code.
    3. Receives the player's name as the first message.
    4. Adds the player if valid and broadcasts the join event.
    5. Keeps the WebSocket alive in a loop until disconnect.
    """
    # Accept the WebSocket connection
    await websocket.accept()
    print(f"WebSocket accepted for code: {code}")

    # If the game code is invalid, notify and close connection
    if code not in games:
        await websocket.send_json({"status": "error", "message": "Invalid game code"})
        await websocket.close()
        return

    game = games[code]
    current_player: Union[Player, None] = None
    try:
        # Expect the first message to contain {'name': <player_name>}
        data = await websocket.receive_json()
        if "name" not in data:
            await websocket.send_json({"status": "error", "message": "First message must contain 'name'."})
            await websocket.close()
            return

        name = data["name"]
        # Reject if game is full
        if game.is_full():
            await websocket.send_json({"status": "error", "message": "Game is full"})
            await websocket.close()
            return
        # Reject duplicate names (case-insensitive)
        if any(p.name.lower() == name.lower() for p in game.players):
            await websocket.send_json({"status": "error", "message": "Name already taken."})
            await websocket.close()
            return

        # Create Player object; first player becomes host
        current_player = Player(
            name=name,
            websocket=websocket,
            is_host=(len(game.players) == 0)
        )
        game.add_player(current_player)
        print(f"Player {name} joined game {code}")

        # Inform all players about the new join
        await game.broadcast({
            "status": "player_joined",
            "player_name": name,
            "players": game.to_dict_list()
        })

        # Keep the connection alive indefinitely
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ready":
                current_player.is_ready = True
                print(f"{current_player.name} is ready in game {code}")
                await game.broadcast({
                    "status": "player_ready",
                    "player_name": current_player.name,
                    "players": game.to_dict_list()
                })

            if all(p.is_ready for p in game.players):
                if len(game.players) > 1:
                    print(f"All players ready in game {code}")
                    await game.broadcast({
                        "status": "game_started"
                    })
                else:
                    await current_player.websocket.send_json({
                        "status": "error",
                        "message": "Bro, you're alone. Invite someone else to start the game."
                    })

    except WebSocketDisconnect:
        # Handle clean-up on disconnect
        if current_player:
            game.remove_player(current_player)
            print(
                f"Player {current_player.name} disconnected from game {code}")
            if game.players:
                # Notify remaining players
                await game.broadcast({
                    "status": "player_left",
                    "player_name": current_player.name,
                    "players": game.to_dict_list()
                })
            else:
                # No players left: remove the game
                del games[code]
                print(f"Game {code} removed - no players left")
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Error in game {code}: {e}")
        if current_player:
            game.remove_player(current_player)
