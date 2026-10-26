import pytest

from chess_game import ChessGame


def test_new_game_starts_with_white():
    game = ChessGame()

    assert game.current_player() == "White"
    assert game.is_game_over() is False
    assert len(list(game.board.legal_moves)) == 20


def test_valid_move_changes_turn():
    game = ChessGame()

    game.play_move("e4")

    assert game.current_player() == "Black"
    assert "1. e4" in game.get_history()


def test_illegal_move_raises_error():
    game = ChessGame()

    with pytest.raises(ValueError):
        game.play_move("e5")

    assert game.current_player() == "White"
    assert game.get_history() == "No moves yet."


def test_fools_mate_ends_the_game():
    game = ChessGame()

    game.play_move("f3")
    game.play_move("e5")
    game.play_move("g4")
    game.play_move("Qh4#")

    assert game.is_game_over() is True
    assert game.get_result() == "0-1"


def test_pgn_contains_played_moves():
    game = ChessGame()

    game.play_move("e4")
    game.play_move("e5")
    game.play_move("Nf3")

    pgn = game.get_pgn()

    assert "1. e4 e5 2. Nf3" in pgn


def test_save_pgn_creates_file(tmp_path):
    game = ChessGame()
    game.play_move("e4")
    game.play_move("e5")

    save_path = tmp_path / "my_game.pgn"
    game.save_pgn(save_path)

    assert save_path.exists()
    assert "1. e4 e5" in save_path.read_text()


def test_load_pgn_restores_game(tmp_path):
    original_game = ChessGame()
    original_game.play_move("e4")
    original_game.play_move("e5")
    original_game.play_move("Nf3")

    save_path = tmp_path / "my_game.pgn"
    original_game.save_pgn(save_path)

    loaded_game = ChessGame.load_pgn(save_path)

    assert loaded_game.get_history() == original_game.get_history()
    assert loaded_game.board.fen() == original_game.board.fen()
    assert loaded_game.current_player() == "Black"

def test_uci_move_is_accepted():
    game = ChessGame()

    game.play_move("e2e4")

    assert game.current_player() == "Black"
    assert game.get_history() == "1. e4"