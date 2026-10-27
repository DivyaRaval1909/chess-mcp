from typing import Dict
from uuid import uuid4
import os
import re
import secrets
import asyncio
from datetime import datetime, timezone

import chess
import jwt
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel

from chess_game import ChessGame

from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from bot import MLChessBot, RandomChessBot, StockfishBot
from database import initialise_database, rooms, users
from ml.inference import get_outcome_probabilities, rank_legal_moves
from security import create_access_token, decode_access_token, hash_password, verify_password



app = FastAPI(title="ML Chess API")
bearer_scheme = HTTPBearer(auto_error=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary storage while the server is running.
# Later, PostgreSQL will replace this.
games: Dict[str, ChessGame] = {
    
}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_BOT_TYPES = {"random", "ml", "stockfish"}
TIME_CONTROL_PRESETS = {
    "bullet": {"initial_seconds": 60, "increment_seconds": 0},
    "blitz": {"initial_seconds": 300, "increment_seconds": 0},
    "rapid": {"initial_seconds": 600, "increment_seconds": 5},
}


@app.on_event("startup")
def connect_to_database():
    initialise_database()

def create_bot():
    bot_type = os.getenv("BOT_TYPE", "random").lower()

    if bot_type == "stockfish":
        engine_path = os.getenv("STOCKFISH_PATH", "stockfish")
        return StockfishBot(engine_path)

    if bot_type == "ml":
        model_path = os.getenv(
            "ML_MODEL_PATH",
            "models/policy_value_v1.pt",
        )
        return MLChessBot(model_path=model_path)

    if bot_type == "random":
        return RandomChessBot()

    raise ValueError(
        "BOT_TYPE must be random, stockfish, or ml"
    )


bot = create_bot()
bot_cache = {}


class RoomConnectionManager:
    def __init__(self):
        self.connections = {}

    async def connect(self, share_code, websocket):
        await websocket.accept()
        self.connections.setdefault(share_code, set()).add(websocket)

    def disconnect(self, share_code, websocket):
        connections = self.connections.get(share_code, set())
        connections.discard(websocket)

        if not connections:
            self.connections.pop(share_code, None)

    async def broadcast(self, share_code, message):
        for websocket in list(self.connections.get(share_code, set())):
            try:
                await websocket.send_json(message)
            except RuntimeError:
                self.disconnect(share_code, websocket)


room_connections = RoomConnectionManager()


def get_room_bot(bot_type):
    if bot_type in bot_cache:
        return bot_cache[bot_type]

    if bot_type == "random":
        room_bot = RandomChessBot()
    elif bot_type == "ml":
        room_bot = MLChessBot(
            model_path=os.getenv("ML_MODEL_PATH", "models/policy_value_v1.pt")
        )
    elif bot_type == "stockfish":
        room_bot = StockfishBot(os.getenv("STOCKFISH_PATH", "stockfish"))
    else:
        raise ValueError("Unknown room bot type")

    bot_cache[bot_type] = room_bot
    return room_bot


class MoveRequest(BaseModel):
    move: str

class CreateGameRequest(BaseModel):
    difficulty: str = "medium"


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RoomCreateRequest(BaseModel):
    mode: str = "human"
    bot_type: str | None = None
    time_control: str = "blitz"
    initial_seconds: int | None = None
    increment_seconds: int | None = None
    rated: bool = False


def public_user(user):
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "elo": user["elo"],
        "created_at": user["created_at"],
    }


def room_snapshot(room):
    clock = room["clock"].copy()

    if room["status"] == "active":
        elapsed_seconds = (
            datetime.now(timezone.utc) - clock["turn_started_at"]
        ).total_seconds()
        active_color = room["game"]["turn"].lower()
        clock[active_color] = max(0, clock[active_color] - elapsed_seconds)

    return {
        "share_code": room["share_code"],
        "status": room["status"],
        "mode": room["mode"],
        "bot_type": room.get("bot_type"),
        "rated": room["rated"],
        "players": {
            "white_user_id": str(room["players"]["white_user_id"]),
            "black_user_id": (
                str(room["players"]["black_user_id"])
                if room["players"].get("black_user_id")
                else None
            ),
        },
        "time_control": room["time_control"],
        "clock": {
            "white_seconds": round(clock["white"], 1),
            "black_seconds": round(clock["black"], 1),
        },
        "game": room["game"],
        "created_at": room["created_at"],
    }


def create_share_code():
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "").upper()


def websocket_user(token):
    from bson import ObjectId

    try:
        token_data = decode_access_token(token)
        return users.find_one({"_id": ObjectId(token_data["sub"])})
    except (jwt.PyJWTError, ValueError):
        return None


def room_player_color(room, user_id):
    if room["players"]["white_user_id"] == user_id:
        return chess.WHITE

    if room["players"].get("black_user_id") == user_id:
        return chess.BLACK

    return None


def apply_clock_and_move(room, board, move):
    now = datetime.now(timezone.utc)
    moving_color = "white" if board.turn == chess.WHITE else "black"
    turn_started_at = room["clock"]["turn_started_at"]

    if turn_started_at.tzinfo is None:
        turn_started_at = turn_started_at.replace(tzinfo=timezone.utc)

    elapsed_seconds = (now - turn_started_at).total_seconds()
    remaining_seconds = room["clock"][moving_color] - elapsed_seconds

    if remaining_seconds <= 0:
        room["status"] = "finished"
        room["game"]["result"] = (
            "0-1 (White flagged)"
            if moving_color == "white"
            else "1-0 (Black flagged)"
        )
        rooms.replace_one({"_id": room["_id"]}, room)
        return False

    move_san = board.san(move)
    board.push(move)
    room["clock"][moving_color] = (
        remaining_seconds + room["time_control"]["increment_seconds"]
    )
    room["clock"]["turn_started_at"] = now
    room["game"]["fen"] = board.fen()
    room["game"]["turn"] = "White" if board.turn == chess.WHITE else "Black"
    room["game"]["move_history"].append(move_san)

    if board.is_game_over(claim_draw=True):
        room["status"] = "finished"
        room["game"]["result"] = board.result(claim_draw=True)

    rooms.replace_one({"_id": room["_id"]}, room)
    return True


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )

    try:
        token_data = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from error

    user = users.find_one({"_id": token_data["sub"]})

    if user is None:
        # ObjectId is stored as a string in JWT, so query again below.
        from bson import ObjectId

        try:
            user = users.find_one({"_id": ObjectId(token_data["sub"])})
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token.",
            ) from error

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )

    return user


def game_state(game: ChessGame):
    return {
        "legal_moves_uci": [move.uci() for move in game.board.legal_moves],
        "fen": game.board.fen(),
        "turn": game.current_player(),
        "legal_moves": [game.board.san(move) for move in game.board.legal_moves],
        "move_history": game.move_history,
        "is_game_over": game.is_game_over(),
        "result": game.get_result() if game.is_game_over() else None,
        "difficulty": game.difficulty,
    }


@app.get("/")
def home():
    return {"message": "ML Chess API is running"}


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    username = request.username.strip().lower()

    if not re.fullmatch(r"[a-z0-9_]{3,20}", username):
        raise HTTPException(
            status_code=400,
            detail="Username must contain 3-20 lowercase letters, numbers, or underscores.",
        )

    if len(request.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters.",
        )

    user = {
        "username": username,
        "password_hash": hash_password(request.password),
        "elo": 1200,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = users.insert_one(user)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=409,
            detail="That username is already taken.",
        ) from error

    user["_id"] = result.inserted_id
    return {
        "access_token": create_access_token(result.inserted_id, username),
        "token_type": "bearer",
        "user": public_user(user),
    }


@app.post("/auth/login")
def login(request: LoginRequest):
    username = request.username.strip().lower()
    user = users.find_one({"username": username})

    if user is None or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    return {
        "access_token": create_access_token(user["_id"], user["username"]),
        "token_type": "bearer",
        "user": public_user(user),
    }


@app.get("/auth/me")
def get_my_profile(current_user=Depends(get_current_user)):
    return public_user(current_user)


@app.get("/time-controls")
def list_time_controls():
    return TIME_CONTROL_PRESETS


@app.post("/rooms", status_code=status.HTTP_201_CREATED)
def create_room(
    request: RoomCreateRequest,
    current_user=Depends(get_current_user),
):
    mode = request.mode.lower()

    if mode not in {"human", "bot"}:
        raise HTTPException(status_code=400, detail="Mode must be human or bot.")

    if request.time_control == "custom":
        initial_seconds = request.initial_seconds
        increment_seconds = request.increment_seconds
    else:
        preset = TIME_CONTROL_PRESETS.get(request.time_control)
        if preset is None:
            raise HTTPException(
                status_code=400,
                detail="Choose bullet, blitz, rapid, or custom time control.",
            )
        initial_seconds = preset["initial_seconds"]
        increment_seconds = preset["increment_seconds"]

    if initial_seconds is None or not 30 <= initial_seconds <= 7200:
        raise HTTPException(
            status_code=400,
            detail="Initial time must be between 30 seconds and 2 hours.",
        )

    if increment_seconds is None:
        increment_seconds = 0

    if not 0 <= increment_seconds <= 60:
        raise HTTPException(
            status_code=400,
            detail="Increment must be between 0 and 60 seconds.",
        )

    bot_type = None
    black_user_id = None
    room_status = "waiting"

    if mode == "bot":
        bot_type = (request.bot_type or "ml").lower()
        if bot_type not in VALID_BOT_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Bot type must be random, ml, or stockfish.",
            )
        room_status = "active"

    room = {
        "share_code": create_share_code(),
        "status": room_status,
        "mode": mode,
        "bot_type": bot_type,
        "rated": request.rated and mode == "human",
        "players": {
            "white_user_id": current_user["_id"],
            "black_user_id": black_user_id,
        },
        "time_control": {
            "name": request.time_control,
            "initial_seconds": initial_seconds,
            "increment_seconds": increment_seconds,
        },
        "clock": {
            "white": float(initial_seconds),
            "black": float(initial_seconds),
            "turn_started_at": datetime.now(timezone.utc),
        },
        "game": {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "turn": "White",
            "move_history": [],
            "result": None,
        },
        "created_at": datetime.now(timezone.utc),
    }

    rooms.insert_one(room)
    return room_snapshot(room)


@app.get("/rooms/{share_code}")
def get_room(share_code: str, current_user=Depends(get_current_user)):
    room = rooms.find_one({"share_code": share_code.upper()})

    if room is None:
        raise HTTPException(status_code=404, detail="Room not found.")

    return room_snapshot(room)


@app.post("/rooms/{share_code}/join")
def join_room(share_code: str, current_user=Depends(get_current_user)):
    room = rooms.find_one({"share_code": share_code.upper()})

    if room is None:
        raise HTTPException(status_code=404, detail="Room not found.")

    if room["mode"] != "human":
        raise HTTPException(status_code=400, detail="Bot rooms cannot be joined.")

    if room["players"]["white_user_id"] == current_user["_id"]:
        raise HTTPException(status_code=400, detail="You already own this room.")

    updated_room = rooms.find_one_and_update(
        {
            "_id": room["_id"],
            "status": "waiting",
            "players.black_user_id": None,
        },
        {
            "$set": {
                "status": "active",
                "players.black_user_id": current_user["_id"],
                "clock.turn_started_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if updated_room is None:
        raise HTTPException(status_code=409, detail="Room is no longer available.")

    return room_snapshot(updated_room)


@app.post("/games")
def create_game(request: CreateGameRequest = CreateGameRequest()):
    difficulty = request.difficulty.lower()

    if difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(
            status_code=400,
            detail="Difficulty must be easy, medium, or hard",
        )

    game_id = str(uuid4())
    game = ChessGame(difficulty=difficulty)

    games[game_id] = game

    return {
        "game_id": game_id,
        "game": game_state(game),
    }

@app.get("/games/{game_id}")
def get_game(game_id: str):
    game = games.get(game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    return game_state(game)


@app.get("/games/{game_id}/analysis")
def analyze_game(game_id: str):
    game = games.get(game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if not isinstance(bot, MLChessBot):
        raise HTTPException(
            status_code=400,
            detail="Analysis is available only when BOT_TYPE=ml.",
        )

    probabilities = get_outcome_probabilities(
        board=game.board,
        model=bot.model,
        device=bot.device,
    )
    predictions = rank_legal_moves(
        board=game.board,
        model=bot.model,
        device=bot.device,
        top_k=5,
    )

    return {
        "fen": game.board.fen(),
        "expected_white_value": (
            probabilities["white_win"] - probabilities["black_win"]
        ),
        "outcome_probabilities": probabilities,
        "top_moves": [
            {
                "uci": move.uci(),
                "san": game.board.san(move),
                "policy_score": score,
            }
            for move, score in predictions
        ],
    }

@app.get("/games/{game_id}/pgn", response_class=PlainTextResponse)
def export_pgn(game_id: str):
    game = games.get(game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    return PlainTextResponse(
        content=game.get_pgn(),
        media_type="application/x-chess-pgn",
        headers={
            "Content-Disposition": f'attachment; filename="game-{game_id}.pgn"'
        },
    )


@app.post("/games/{game_id}/moves")
def make_move(game_id: str, move_request: MoveRequest):
    game = games.get(game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.is_game_over():
        raise HTTPException(status_code=400, detail="This game is already over")

    try:
        game.play_move(move_request.move)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Illegal or invalid move: {move_request.move}",
        )

    return game_state(game)

@app.post("/games/{game_id}/bot-move")
def make_bot_move(game_id: str):
    game = games.get(game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.is_game_over():
        raise HTTPException(status_code=400, detail="This game is already over")

    bot_move = bot.choose_move(game.board)

    if bot_move is None:
        raise HTTPException(status_code=400, detail="No legal moves available")

    game.play_move(bot_move)

    return {
        "bot_move": bot_move,
        "game": game_state(game),
    }

@app.post("/games/{game_id}/human-move")
def make_human_move(game_id: str, move_request: MoveRequest):
    game = games.get(game_id)

    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.is_game_over():
        raise HTTPException(status_code=400, detail="This game is already over")

    if game.current_player() != "White":
        raise HTTPException(
            status_code=400,
            detail="It is not the human player's turn",
        )

    try:
        game.play_move(move_request.move)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Illegal or invalid move: {move_request.move}",
        )

    # If the human's move ended the game, there is no bot response.
    if game.is_game_over():
        return {
            "human_move": move_request.move,
            "bot_move": None,
            "game": game_state(game),
        }

    bot_move = bot.choose_move(game.board, game.difficulty)
    game.play_move(bot_move)

    return {
        "human_move": move_request.move,
        "bot_move": bot_move,
        "game": game_state(game),
    }
