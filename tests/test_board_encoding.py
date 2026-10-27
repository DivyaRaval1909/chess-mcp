import chess

from ml.board_encoding import encode_board


def test_encoded_board_has_expected_shape():
    board = chess.Board()

    encoded_board = encode_board(board)

    assert encoded_board.shape == (18, 8, 8)


def test_starting_position_contains_32_pieces():
    board = chess.Board()

    encoded_board = encode_board(board)

    assert encoded_board[:12].sum() == 32


def test_white_pawn_at_e2_is_encoded_correctly():
    board = chess.Board()

    encoded_board = encode_board(board)

    white_pawn_plane = 0
    e2_row = 6
    e2_column = 4

    assert encoded_board[white_pawn_plane, e2_row, e2_column] == 1.0


def test_black_pawn_at_e7_is_encoded_correctly():
    board = chess.Board()

    encoded_board = encode_board(board)

    black_pawn_plane = 6
    e7_row = 1
    e7_column = 4

    assert encoded_board[black_pawn_plane, e7_row, e7_column] == 1.0


def test_starting_position_has_white_to_move_plane():
    board = chess.Board()

    encoded_board = encode_board(board)

    assert encoded_board[12].sum() == 64


def test_starting_position_has_all_castling_rights():
    board = chess.Board()

    encoded_board = encode_board(board)

    assert encoded_board[13].sum() == 64
    assert encoded_board[14].sum() == 64
    assert encoded_board[15].sum() == 64
    assert encoded_board[16].sum() == 64
