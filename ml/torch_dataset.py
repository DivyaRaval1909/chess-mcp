import numpy as np
import torch
from torch.utils.data import Dataset


class ChessMoveDataset(Dataset):
    def __init__(self, dataset_path):
        with np.load(dataset_path) as dataset:
            self.positions = dataset["positions"]
            self.moves = dataset["moves"]
            self.outcomes = dataset["outcomes"]

    def __len__(self):
        return len(self.moves)

    def __getitem__(self, index):
        position = torch.from_numpy(self.positions[index]).float()
        move = torch.tensor(self.moves[index], dtype=torch.long)
        outcome = torch.tensor(self.outcomes[index], dtype=torch.long)

        return position, move, outcome
