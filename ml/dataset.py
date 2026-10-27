import argparse
from pathlib import Path

import chess.pgn
import numpy as np

from ml.board_encoding import encode_board
from ml.move_encoding import encode_move

RESULT_TO_CLASS = {
    "0-1": 0,
    "1/2-1/2": 1,
    "1-0": 2,
}


def create_examples_from_pgn(pgn_path, max_games=None):
    positions = []
    moves = []
    outcomes = []
    game_ids = []
    games_read = 0

    with open(pgn_path, "r", encoding="utf-8") as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)

            if game is None:
                break

            result = game.headers.get("Result", "*")

            # A value model needs the final result of each game.
            if result not in RESULT_TO_CLASS:
                continue

            outcome_class = RESULT_TO_CLASS[result]
            board = game.board()

            for move in game.mainline_moves():
                positions.append(encode_board(board))
                moves.append(encode_move(move))
                outcomes.append(outcome_class)
                game_ids.append(games_read)
                board.push(move)

            games_read += 1

            if max_games is not None and games_read >= max_games:
                break

    if not positions:
        raise ValueError("No playable moves with known results were found.")

    return (
        np.stack(positions),
        np.array(moves, dtype=np.int64),
        np.array(outcomes, dtype=np.int64),
        np.array(game_ids, dtype=np.int64),
    )


def save_dataset(pgn_path, output_path, max_games=None):
    positions, moves, outcomes, game_ids = create_examples_from_pgn(
        pgn_path=pgn_path,
        max_games=max_games,
    )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        output_file,
        positions=positions,
        moves=moves,
        outcomes=outcomes,
        game_ids=game_ids,
    )

    return len(moves)


def main():
    parser = argparse.ArgumentParser(
        description="Convert chess PGN games into an ML dataset."
    )

    parser.add_argument("pgn_path")
    parser.add_argument("output_path")
    parser.add_argument("--max-games", type=int, default=None)

    arguments = parser.parse_args()

    example_count = save_dataset(
        pgn_path=arguments.pgn_path,
        output_path=arguments.output_path,
        max_games=arguments.max_games,
    )

    print(f"Saved {example_count} training examples to {arguments.output_path}")


if __name__ == "__main__":
    main()
