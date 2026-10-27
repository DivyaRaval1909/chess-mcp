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

NUMBER_OF_INPUT_PLANES = 18


def encode_board(board):
    encoded_board = np.zeros(
        (NUMBER_OF_INPUT_PLANES, 8, 8),
        dtype=np.float32,
    )

    for square, piece in board.piece_map().items():
        plane = PIECE_TO_PLANE[piece.piece_type]

        if piece.color == chess.BLACK:
            plane += 6

        row = 7 - chess.square_rank(square)
        column = chess.square_file(square)

        encoded_board[plane, row, column] = 1.0

    # Plane 12: side to move.
    if board.turn == chess.WHITE:
        encoded_board[12, :, :] = 1.0

    # Planes 13–16: castling rights.
    if board.has_kingside_castling_rights(chess.WHITE):
        encoded_board[13, :, :] = 1.0

    if board.has_queenside_castling_rights(chess.WHITE):
        encoded_board[14, :, :] = 1.0

    if board.has_kingside_castling_rights(chess.BLACK):
        encoded_board[15, :, :] = 1.0

    if board.has_queenside_castling_rights(chess.BLACK):
        encoded_board[16, :, :] = 1.0

    # Plane 17: en-passant target square.
    if board.ep_square is not None:
        row = 7 - chess.square_rank(board.ep_square)
        column = chess.square_file(board.ep_square)

        encoded_board[17, row, column] = 1.0

    return encoded_board