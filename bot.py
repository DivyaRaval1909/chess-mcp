import random

import chess
import chess.engine


class RandomChessBot:
    def choose_move(self, board, difficulty="medium"):
        legal_moves = list(board.legal_moves)

        if not legal_moves:
            return None

        selected_move = random.choice(legal_moves)
        return board.san(selected_move)


class StockfishBot:
    DIFFICULTY_PROFILES = {
        "easy": {
            "skill_level": 0,
            "move_time": 0.05,
        },
        "medium": {
            "skill_level": 8,
            "move_time": 0.2,
        },
        "hard": {
            "skill_level": 20,
            "move_time": 0.7,
        },
    }

    def __init__(self, engine_path):
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)

    def choose_move(self, board, difficulty="medium"):
        profile = self.DIFFICULTY_PROFILES.get(
            difficulty,
            self.DIFFICULTY_PROFILES["medium"],
        )

        self.engine.configure(
            {
                "Skill Level": profile["skill_level"],
            }
        )

        result = self.engine.play(
            board,
            chess.engine.Limit(time=profile["move_time"]),
        )

        return board.san(result.move)

    def close(self):
        self.engine.quit()