import numpy as np

from ml.split_dataset import split_dataset


def test_split_keeps_games_separate(tmp_path):
    input_path = tmp_path / "input.npz"
    train_path = tmp_path / "train.npz"
    validation_path = tmp_path / "validation.npz"

    positions = np.zeros((6, 18, 8, 8), dtype=np.float32)
    moves = np.arange(6)
    outcomes = np.array([2, 2, 1, 1, 0, 0])
    game_ids = np.array([0, 0, 1, 1, 2, 2])

    np.savez_compressed(
        input_path,
        positions=positions,
        moves=moves,
        outcomes=outcomes,
        game_ids=game_ids,
    )

    train_count, validation_count = split_dataset(
        input_path=input_path,
        train_output_path=train_path,
        validation_output_path=validation_path,
        validation_fraction=0.33,
        seed=42,
    )

    assert train_count + validation_count == 6

    with np.load(train_path) as train_data:
        train_moves = set(train_data["moves"])
        train_outcomes = train_data["outcomes"]

    with np.load(validation_path) as validation_data:
        validation_moves = set(validation_data["moves"])
        validation_outcomes = validation_data["outcomes"]

    assert train_moves.isdisjoint(validation_moves)
    assert len(train_outcomes) + len(validation_outcomes) == 6
