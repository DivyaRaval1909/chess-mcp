import chess
import numpy as np


PIECE_TO_PLANE = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
    chess.KING: 5,
}


def encode_board(board):
    encoded_board = np.zeros((12, 8, 8), dtype=np.float32)

    for square, piece in board.piece_map().items():
        plane = PIECE_TO_PLANE[piece.piece_type]

        if piece.color == chess.BLACK:
            plane += 6

        row = 7 - chess.square_rank(square)
        column = chess.square_file(square)

        encoded_board[plane, row, column] = 1.0

    return encoded_board