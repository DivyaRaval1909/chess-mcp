from torch import nn

from ml.move_encoding import NUMBER_OF_MOVE_CLASSES


class ChessPolicyNetwork(nn.Module):
    def __init__(self):
        super().__init__()

        self.feature_extractor = nn.Sequential(
            nn.Conv2d(18, 32, kernel_size=3, padding=1),
            nn.ReLU(),

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
        )

        self.shared_layers = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 8 * 8, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
        )

        self.policy_head = nn.Linear(256, NUMBER_OF_MOVE_CLASSES)
        self.value_head = nn.Linear(256, 3)

    def forward(self, board_positions):
        features = self.feature_extractor(board_positions)
        shared_features = self.shared_layers(features)

        return self.policy_head(shared_features), self.value_head(shared_features)
