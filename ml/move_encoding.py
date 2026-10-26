import chess


PROMOTION_TO_CODE = {
    None: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
}

CODE_TO_PROMOTION = {
    0: None,
    1: chess.KNIGHT,
    2: chess.BISHOP,
    3: chess.ROOK,
    4: chess.QUEEN,
}

NUMBER_OF_MOVE_CLASSES = 64 * 64 * 5


def encode_move(move):
    promotion_code = PROMOTION_TO_CODE[move.promotion]

    return ((move.from_square * 64) + move.to_square) * 5 + promotion_code


def decode_move(move_index):
    promotion_code = move_index % 5
    square_index = move_index // 5

    to_square = square_index % 64
    from_square = square_index // 64

    return chess.Move(
        from_square=from_square,
        to_square=to_square,
        promotion=CODE_TO_PROMOTION[promotion_code],
    )