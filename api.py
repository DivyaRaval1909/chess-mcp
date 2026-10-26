from typing import Dict
from uuid import uuid4
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from chess_game import ChessGame

from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from bot import RandomChessBot, StockfishBot



app = FastAPI(title="ML Chess API")
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

def create_bot():
    bot_type = os.getenv("BOT_TYPE", "random").lower()

    if bot_type == "stockfish":
        engine_path = os.getenv("STOCKFISH_PATH", "stockfish")
        move_time = float(os.getenv("STOCKFISH_MOVE_TIME", "0.3"))

        return StockfishBot(
            engine_path=engine_path,
            move_time=move_time,
        )

    return RandomChessBot()


bot = create_bot()


class MoveRequest(BaseModel):
    move: str

class CreateGameRequest(BaseModel):
    difficulty: str = "medium"


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