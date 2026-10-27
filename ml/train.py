import argparse
from pathlib import Path

import torch
from torch import nn
from torch.optim import AdamW
from torch.utils.data import DataLoader

from ml.model import ChessPolicyNetwork
from ml.torch_dataset import ChessMoveDataset


def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")

    if torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def run_epoch(
    model,
    data_loader,
    policy_loss_function,
    value_loss_function,
    optimizer,
    device,
    value_loss_weight,
):
    is_training = optimizer is not None

    if is_training:
        model.train()
    else:
        model.eval()

    total_policy_loss = 0.0
    total_value_loss = 0.0
    correct_move_predictions = 0
    correct_value_predictions = 0
    total_examples = 0

    for positions, target_moves, target_outcomes in data_loader:
        positions = positions.to(device)
        target_moves = target_moves.to(device)
        target_outcomes = target_outcomes.to(device)

        if is_training:
            optimizer.zero_grad()

        with torch.set_grad_enabled(is_training):
            move_scores, value_scores = model(positions)
            policy_loss = policy_loss_function(move_scores, target_moves)
            value_loss = value_loss_function(value_scores, target_outcomes)
            loss = policy_loss + value_loss_weight * value_loss

            if is_training:
                loss.backward()
                optimizer.step()

        batch_size = positions.size(0)

        total_policy_loss += policy_loss.item() * batch_size
        total_value_loss += value_loss.item() * batch_size
        correct_move_predictions += (
            move_scores.argmax(dim=1) == target_moves
        ).sum().item()
        correct_value_predictions += (
            value_scores.argmax(dim=1) == target_outcomes
        ).sum().item()
        total_examples += batch_size

    return {
        "policy_loss": total_policy_loss / total_examples,
        "value_loss": total_value_loss / total_examples,
        "policy_accuracy": correct_move_predictions / total_examples,
        "value_accuracy": correct_value_predictions / total_examples,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Train a chess policy-and-value model."
    )

    parser.add_argument("--train-data", required=True)
    parser.add_argument("--validation-data", required=True)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--value-loss-weight", type=float, default=1.0)
    parser.add_argument(
        "--output",
        default="models/policy_value_v1.pt",
    )

    arguments = parser.parse_args()

    torch.manual_seed(42)

    device = get_device()
    print(f"Training device: {device}")

    training_dataset = ChessMoveDataset(arguments.train_data)
    validation_dataset = ChessMoveDataset(arguments.validation_data)

    training_loader = DataLoader(
        training_dataset,
        batch_size=arguments.batch_size,
        shuffle=True,
    )

    validation_loader = DataLoader(
        validation_dataset,
        batch_size=arguments.batch_size,
        shuffle=False,
    )

    model = ChessPolicyNetwork().to(device)
    policy_loss_function = nn.CrossEntropyLoss()
    value_loss_function = nn.CrossEntropyLoss()
    optimizer = AdamW(model.parameters(), lr=arguments.learning_rate)

    print(f"Training examples: {len(training_dataset)}")
    print(f"Validation examples: {len(validation_dataset)}")

    for epoch in range(1, arguments.epochs + 1):
        training_metrics = run_epoch(
            model=model,
            data_loader=training_loader,
            policy_loss_function=policy_loss_function,
            value_loss_function=value_loss_function,
            optimizer=optimizer,
            device=device,
            value_loss_weight=arguments.value_loss_weight,
        )

        validation_metrics = run_epoch(
            model=model,
            data_loader=validation_loader,
            policy_loss_function=policy_loss_function,
            value_loss_function=value_loss_function,
            optimizer=None,
            device=device,
            value_loss_weight=arguments.value_loss_weight,
        )

        print(
            f"Epoch {epoch}/{arguments.epochs} | "
            f"train policy loss: {training_metrics['policy_loss']:.4f} | "
            f"train policy accuracy: {training_metrics['policy_accuracy']:.2%} | "
            f"train value loss: {training_metrics['value_loss']:.4f} | "
            f"train value accuracy: {training_metrics['value_accuracy']:.2%} | "
            f"validation policy loss: {validation_metrics['policy_loss']:.4f} | "
            f"validation policy accuracy: {validation_metrics['policy_accuracy']:.2%} | "
            f"validation value loss: {validation_metrics['value_loss']:.4f} | "
            f"validation value accuracy: {validation_metrics['value_accuracy']:.2%}"
        )

    output_path = Path(arguments.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "training_examples": len(training_dataset),
            "validation_examples": len(validation_dataset),
            "model_type": "policy_value",
            "value_loss_weight": arguments.value_loss_weight,
        },
        output_path,
    )

    print(f"Saved trained model to {output_path}")


if __name__ == "__main__":
    main()
