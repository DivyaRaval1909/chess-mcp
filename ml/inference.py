import argparse

import chess
import numpy as np
import torch

from ml.board_encoding import encode_board
from ml.model import ChessPolicyNetwork
from ml.move_encoding import encode_move


def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")

    if torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def load_model(model_path, device):
    checkpoint = torch.load(
        model_path,
        map_location=device,
    )

    model = ChessPolicyNetwork()
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    return model


def rank_legal_moves(board, model, device, top_k=5):
    encoded_board = encode_board(board)

    model_input = torch.from_numpy(encoded_board)
    model_input = model_input.unsqueeze(0).to(device)

    with torch.no_grad():
        move_scores, _ = model(model_input)
        move_scores = move_scores.squeeze(0).cpu()

    legal_moves = list(board.legal_moves)

    legal_move_scores = [
        (
            move,
            move_scores[encode_move(move)].item(),
        )
        for move in legal_moves
    ]

    legal_move_scores.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return legal_move_scores[:top_k]


def evaluate_position(board, model, device):
    """Return the expected result from White's perspective, from -1 to 1."""
    return evaluate_boards([board], model, device)[0]


def evaluate_boards(boards, model, device):
    """Evaluate several boards at once from White's perspective."""
    if not boards:
        return []

    encoded_boards = np.stack([encode_board(board) for board in boards])
    model_input = torch.from_numpy(encoded_boards).to(device)

    with torch.no_grad():
        _, value_scores = model(model_input)
        probabilities = torch.softmax(value_scores, dim=1).cpu()

    return (probabilities[:, 2] - probabilities[:, 0]).tolist()


def get_outcome_probabilities(board, model, device):
    """Return outcome probabilities in the order used by the value head."""
    encoded_board = encode_board(board)
    model_input = torch.from_numpy(encoded_board).unsqueeze(0).to(device)

    with torch.no_grad():
        _, value_scores = model(model_input)
        probabilities = torch.softmax(value_scores, dim=1).squeeze(0).cpu()

    return {
        "black_win": probabilities[0].item(),
        "draw": probabilities[1].item(),
        "white_win": probabilities[2].item(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Show the model's top predicted legal chess moves."
    )

    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--fen",
        default=chess.STARTING_FEN,
    )
    parser.add_argument("--top-k", type=int, default=5)

    arguments = parser.parse_args()

    device = get_device()
    board = chess.Board(arguments.fen)
    model = load_model(arguments.model, device)

    predictions = rank_legal_moves(
        board=board,
        model=model,
        device=device,
        top_k=arguments.top_k,
    )

    print(f"Position: {board.fen()}")
    print("\nTop predicted legal moves:")

    for rank, (move, score) in enumerate(predictions, start=1):
        print(f"{rank}. {board.san(move)}  (score: {score:.3f})")


if __name__ == "__main__":
    main()
