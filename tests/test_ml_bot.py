import chess
import torch

from bot import MLChessBot
from ml.model import ChessPolicyNetwork


def test_ml_bot_returns_a_legal_move():
    board = chess.Board()

    bot = MLChessBot(
        model=ChessPolicyNetwork(),
        device=torch.device("cpu"),
    )

    selected_move = bot.choose_move(board)

    legal_moves = [
        board.san(move)
        for move in board.legal_moves
    ]

    assert selected_move in legal_moves
    assert board.fen() == chess.STARTING_FEN
