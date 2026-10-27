import random

import chess
import chess.engine
from ml.inference import (
    evaluate_boards,
    get_device,
    load_model,
    rank_legal_moves,
)


class RandomChessBot:
    def choose_move(self, board, difficulty="medium"):
        legal_moves = list(board.legal_moves)

        if not legal_moves:
            return None

        selected_move = random.choice(legal_moves)
        return board.san(selected_move)


class StockfishBot:
    DIFFICULTY_PROFILES = {
        "easy": {"skill_level": 0, "move_time": 0.05},
        "medium": {"skill_level": 8, "move_time": 0.2},
        "hard": {"skill_level": 20, "move_time": 0.7},
    }

    def __init__(self, engine_path):
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)

    def choose_move(self, board, difficulty="medium"):
        profile = self.DIFFICULTY_PROFILES.get(
            difficulty,
            self.DIFFICULTY_PROFILES["medium"],
        )

        self.engine.configure(
            {"Skill Level": profile["skill_level"]}
        )

        result = self.engine.play(
            board,
            chess.engine.Limit(time=profile["move_time"]),
        )

        return board.san(result.move)

    def close(self):
        self.engine.quit()


class MLChessBot:
    SEARCH_PROFILES = {
        "easy": {"candidate_count": 3, "reply_count": 1},
        "medium": {"candidate_count": 5, "reply_count": 2},
        "hard": {"candidate_count": 8, "reply_count": 3},
    }

    def __init__(self, model_path=None, model=None, device=None):
        self.device = device or get_device()

        if model is not None:
            self.model = model.to(self.device)
            self.model.eval()
        else:
            self.model = load_model(model_path, self.device)

    def choose_move(self, board, difficulty="medium"):
        search_profile = self.SEARCH_PROFILES.get(
            difficulty,
            self.SEARCH_PROFILES["medium"],
        )

        predictions = rank_legal_moves(
            board=board,
            model=self.model,
            device=self.device,
            top_k=search_profile["candidate_count"],
        )

        if not predictions:
            return None

        bot_color = board.turn
        candidate_leaf_values = {
            move: []
            for move, _ in predictions
        }
        boards_to_evaluate = []
        board_owners = []

        for move, _ in predictions:
            board.push(move)

            if board.is_game_over():
                candidate_leaf_values[move].append(
                    self._terminal_white_value(board)
                )
            else:
                replies = rank_legal_moves(
                    board=board,
                    model=self.model,
                    device=self.device,
                    top_k=search_profile["reply_count"],
                )

                for reply, _ in replies:
                    board.push(reply)
                    boards_to_evaluate.append(board.copy())
                    board_owners.append(move)
                    board.pop()

            board.pop()

        evaluated_values = evaluate_boards(
            boards=boards_to_evaluate,
            model=self.model,
            device=self.device,
        )

        for move, white_value in zip(board_owners, evaluated_values):
            candidate_leaf_values[move].append(white_value)

        candidate_values = []

        for move, _ in predictions:
            bot_values = [
                white_value if bot_color == chess.WHITE else -white_value
                for white_value in candidate_leaf_values[move]
            ]

            # Opponent is assumed to choose the reply worst for the bot.
            candidate_values.append((move, min(bot_values)))

        best_move, _ = max(candidate_values, key=lambda item: item[1])

        return board.san(best_move)

    @staticmethod
    def _terminal_white_value(board):
        outcome = board.outcome(claim_draw=True)

        if outcome.winner == chess.WHITE:
            return 1.0

        if outcome.winner == chess.BLACK:
            return -1.0

        return 0.0
