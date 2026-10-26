import argparse
from pathlib import Path

import numpy as np


def split_dataset(
    input_path,
    train_output_path,
    validation_output_path,
    validation_fraction=0.1,
    seed=42,
):
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1.")

    with np.load(input_path) as dataset:
        positions = dataset["positions"]
        moves = dataset["moves"]
        game_ids = dataset["game_ids"]

    unique_game_ids = np.unique(game_ids)

    random_generator = np.random.default_rng(seed)
    random_generator.shuffle(unique_game_ids)

    validation_game_count = max(
        1,
        round(len(unique_game_ids) * validation_fraction),
    )

    validation_game_ids = unique_game_ids[:validation_game_count]

    validation_mask = np.isin(game_ids, validation_game_ids)
    training_mask = ~validation_mask

    Path(train_output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(validation_output_path).parent.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        train_output_path,
        positions=positions[training_mask],
        moves=moves[training_mask],
    )

    np.savez_compressed(
        validation_output_path,
        positions=positions[validation_mask],
        moves=moves[validation_mask],
    )

    return training_mask.sum(), validation_mask.sum()


def main():
    parser = argparse.ArgumentParser(
        description="Split a chess ML dataset into training and validation sets."
    )

    parser.add_argument("input_path")
    parser.add_argument("train_output_path")
    parser.add_argument("validation_output_path")
    parser.add_argument(
        "--validation-fraction",
        type=float,
        default=0.1,
    )

    arguments = parser.parse_args()

    train_count, validation_count = split_dataset(
        input_path=arguments.input_path,
        train_output_path=arguments.train_output_path,
        validation_output_path=arguments.validation_output_path,
        validation_fraction=arguments.validation_fraction,
    )

    print(f"Training examples: {train_count}")
    print(f"Validation examples: {validation_count}")


if __name__ == "__main__":
    main()