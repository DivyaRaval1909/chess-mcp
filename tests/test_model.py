import torch

from ml.model import ChessPolicyNetwork
from ml.move_encoding import NUMBER_OF_MOVE_CLASSES


def test_model_output_shape():
    model = ChessPolicyNetwork()

    sample_positions = torch.zeros((4, 18, 8, 8))

    move_scores, value_scores = model(sample_positions)

    assert move_scores.shape == (4, NUMBER_OF_MOVE_CLASSES)
    assert value_scores.shape == (4, 3)


def test_model_outputs_support_training():
    model = ChessPolicyNetwork()

    sample_positions = torch.zeros((1, 18, 8, 8))
    move_scores, value_scores = model(sample_positions)

    assert move_scores.requires_grad is True
    assert value_scores.requires_grad is True
