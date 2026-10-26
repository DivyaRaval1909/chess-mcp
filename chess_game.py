from pathlib import Path

import chess
import chess.pgn


class ChessGame:
    def __init__(self, difficulty="medium"):
        self.board = chess.Board()
        self.difficulty = difficulty
        self.move_history = []

    def current_player(self):
        if self.board.turn == chess.WHITE:
            return "White"
        return "Black"

    def play_move(self, move_text):
        try:
          move = self.board.parse_san(move_text)
        except ValueError:
          move = self.board.parse_uci(move_text)
 
        self._record_and_play_move(move)

    def _record_and_play_move(self, move):
        move_number = self.board.fullmove_number
        san_move = self.board.san(move)

        if self.board.turn == chess.WHITE:
            self.move_history.append(f"{move_number}. {san_move}")
        else:
            self.move_history.append(san_move)

        self.board.push(move)

    def get_history(self):
        if not self.move_history:
            return "No moves yet."

        return " ".join(self.move_history)

    def get_pgn(self):
        game = chess.pgn.Game.from_board(self.board)
        return str(game)

    def save_pgn(self, file_path):
        Path(file_path).write_text(self.get_pgn(), encoding="utf-8")

    @classmethod
    def load_pgn(cls, file_path):
        with open(file_path, "r", encoding="utf-8") as pgn_file:
            saved_game = chess.pgn.read_game(pgn_file)

        if saved_game is None:
            raise ValueError("No valid PGN game was found in this file.")

        chess_game = cls()

        for move in saved_game.mainline_moves():
            chess_game._record_and_play_move(move)

        return chess_game

    def is_game_over(self):
        return self.board.is_game_over()

    def get_result(self):
        return self.board.result()