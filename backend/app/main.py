import asyncio
from typing import Dict, Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .lib.game import Game
from .lib.utils import generate_game_code
from .models.player import Player

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

games: Dict[str, "Game"] = {}


@app.post("/create")
async def create_game_http():
    """
    HTTP endpoint to create a new game.
    Generates a unique code and initializes a Game instance.
    """
    code = generate_game_code()
    while code in games:
        code = generate_game_code()

    games[code] = Game(code)
    print(f"New game created: {code}")
    return {"success": True, "code": code}


@app.get("/check_code/{code}")
async def check_code(code: str):
    """
    HTTP endpoint to verify if a game code exists and is not full.
    """
    game = games.get(code)
    if game:
        return {"exists": True, "full": game.is_full()}
    return {"exists": False, "full": False}


@app.websocket("/ws/game/{code}")
async def game_ws(websocket: WebSocket, code: str):
    """
    WebSocket endpoint for handling game connections and events.
    """
    await websocket.accept()
    game = games.get(code)

    if not game:
        await websocket.send_json({"status": "error", "message": "Invalid game code"})
        await websocket.close()
        return

    current_player: Union[Player, None] = None
    try:
        # 1. First message is for player registration
        data = await websocket.receive_json()
        player_name = data.get("name")

        if not player_name:
            await websocket.send_json({"status": "error", "message": "Player name is required."})
            return

        if game.is_full():
            await websocket.send_json({"status": "error", "message": "This game is full."})
            return

        if any(p.name.lower() == player_name.lower() for p in game.players):
            await websocket.send_json({"status": "error", "message": "This name is already taken."})
            return

        is_host = not game.players
        current_player = Player(
            name=player_name, websocket=websocket, is_host=is_host)
        game.add_player(current_player)
        print(f"Player '{current_player.name}' joined game {code}")

        await game.broadcast({
            "status": "player_joined",
            "player": current_player.to_dict(),
            "players": game.to_dict_list()
        })

        # 2. Main game loop for handling player actions
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "ready":
                current_player.is_ready = data.get("is_ready", True)
                print(
                    f"Player '{current_player.name}' readiness changed to {current_player.is_ready} in game {code}")
                await game.broadcast({
                    "status": "player_ready",
                    "player_id": current_player.id,
                    "is_ready": current_player.is_ready,
                })

                # Check if all players are ready to start
                if len(game.players) > 1 and all(p.is_ready for p in game.players):
                    print(
                        f"All players are ready in game {code}. Starting game.")
                    await game.start_game()

            elif message_type == "move" and game.started:
                if game.order.get_current_player().id == current_player.id:
                    await game.process_move(current_player, data.get("move"))
                    if len(current_player.hand) == 1:
                        await game.start_colo_challenge(
                            player=current_player,
                            broadcast_callback=game.broadcast
                        )
                else:
                    await websocket.send_json({"status": "error", "message": "It's not your turn."})

            elif message_type == "draw_card" and game.started:
                if game.order.get_current_player().id == current_player.id:
                    await game.draw_card(current_player)
                else:
                    await websocket.send_json({"status": "error", "message": "It's not your turn."})

            elif message_type == "colo":
                await game.colo_pressed(
                    caller=current_player,
                    draw_card_callback=game.draw_card,
                    broadcast_callback=game.broadcast
                )

    except WebSocketDisconnect:
        print(
            f"Player '{current_player.name if current_player else 'Unknown'}' disconnected from game {code}")
    except Exception as e:
        print(f"An unexpected error occurred in game {code}: {e}")
    finally:
        # Cleanup on disconnect or error
        if current_player:
            game.remove_player(current_player)
            if game.players:
                await game.broadcast({
                    "status": "player_left",
                    "player_id": current_player.id,
                    "players": game.to_dict_list()
                })
            else:
                # If no players are left, remove the game from memory
                del games[code]
                print(f"Game {code} has been closed.")
