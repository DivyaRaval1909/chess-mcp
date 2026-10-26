from ml.dataset import create_examples_from_pgn


def test_create_examples_from_pgn(tmp_path):
    pgn_path = tmp_path / "sample_game.pgn"

    pgn_path.write_text(
        """
[Event "Test game"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *
""".strip(),
        encoding="utf-8",
    )

    positions, moves, game_ids = create_examples_from_pgn(pgn_path)

    assert positions.shape == (6, 12, 8, 8)
    assert moves.shape == (6,)
    assert game_ids.shape == (6,)
    assert len(set(game_ids)) == 1
