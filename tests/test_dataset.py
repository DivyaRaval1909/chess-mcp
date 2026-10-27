from ml.dataset import create_examples_from_pgn


def test_create_examples_from_pgn(tmp_path):
    pgn_path = tmp_path / "sample_game.pgn"

    pgn_path.write_text(
        """
[Event "Test game"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
""".strip(),
        encoding="utf-8",
    )

    positions, moves, outcomes, game_ids = create_examples_from_pgn(pgn_path)

    assert positions.shape == (6, 18, 8, 8)
    assert moves.shape == (6,)
    assert outcomes.shape == (6,)
    assert game_ids.shape == (6,)
    assert set(outcomes) == {2}
    assert len(set(game_ids)) == 1
