import chess

from ml.move_encoding import (
    NUMBER_OF_MOVE_CLASSES,
    decode_move,
    encode_move,
)


def test_total_number_of_move_classes():
    assert NUMBER_OF_MOVE_CLASSES == 20480


def test_encode_and_decode_standard_move():
    move = chess.Move.from_uci("e2e4")

    move_index = encode_move(move)
    decoded_move = decode_move(move_index)

    assert decoded_move == move


def test_encode_and_decode_queen_promotion():
    move = chess.Move.from_uci("a7a8q")

    move_index = encode_move(move)
    decoded_move = decode_move(move_index)

    assert decoded_move == move


def test_encode_and_decode_knight_promotion():
    move = chess.Move.from_uci("b7b8n")

    move_index = encode_move(move)
    decoded_move = decode_move(move_index)

    assert decoded_move == move