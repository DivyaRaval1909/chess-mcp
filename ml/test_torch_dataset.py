import numpy as np
from torch.utils.data import DataLoader

from ml.torch_dataset import ChessMoveDataset


def test_torch_dataset_returns_position_and_move(tmp_path):
    dataset_path = tmp_path / "sample_dataset.npz"

    positions = np.zeros((3, 18, 8, 8), dtype=np.float32)
    moves = np.array([1, 2, 3], dtype=np.int64)
    outcomes = np.array([2, 1, 0], dtype=np.int64)

    np.savez_compressed(
        dataset_path,
        positions=positions,
        moves=moves,
        outcomes=outcomes,
    )

    dataset = ChessMoveDataset(dataset_path)

    position, move, outcome = dataset[0]

    assert len(dataset) == 3
    assert position.shape == (18, 8, 8)
    assert move.item() == 1
    assert outcome.item() == 2


def test_data_loader_creates_batches(tmp_path):
    dataset_path = tmp_path / "sample_dataset.npz"

    positions = np.zeros((4, 18, 8, 8), dtype=np.float32)
    moves = np.array([1, 2, 3, 4], dtype=np.int64)
    outcomes = np.array([2, 1, 0, 2], dtype=np.int64)

    np.savez_compressed(
        dataset_path,
        positions=positions,
        moves=moves,
        outcomes=outcomes,
    )

    dataset = ChessMoveDataset(dataset_path)
    data_loader = DataLoader(dataset, batch_size=2)

    positions_batch, moves_batch, outcomes_batch = next(iter(data_loader))

    assert positions_batch.shape == (2, 18, 8, 8)
    assert moves_batch.shape == (2,)
    assert outcomes_batch.shape == (2,)
