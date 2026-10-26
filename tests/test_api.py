from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "ML Chess API is running"}


def test_create_game():
    response = client.post("/games")

    assert response.status_code == 200

    data = response.json()

    assert "game_id" in data
    assert data["game"]["turn"] == "White"
    assert len(data["game"]["legal_moves"]) == 20
    assert "e2e4" in data["game"]["legal_moves_uci"]


def test_make_legal_move():
    create_response = client.post("/games")
    game_id = create_response.json()["game_id"]

    move_response = client.post(
        f"/games/{game_id}/moves",
        json={"move": "e4"},
    )

    assert move_response.status_code == 200

    data = move_response.json()

    assert data["turn"] == "Black"
    assert data["move_history"] == ["1. e4"]


def test_reject_illegal_move():
    create_response = client.post("/games")
    game_id = create_response.json()["game_id"]

    move_response = client.post(
        f"/games/{game_id}/moves",
        json={"move": "e5"},
    )

    assert move_response.status_code == 400
    assert "Illegal or invalid move" in move_response.json()["detail"]


def test_unknown_game_returns_404():
    response = client.get("/games/not-a-real-game-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"


def test_export_game_as_pgn():
    create_response = client.post("/games")
    game_id = create_response.json()["game_id"]

    client.post(
        f"/games/{game_id}/moves",
        json={"move": "e4"},
    )

    client.post(
        f"/games/{game_id}/moves",
        json={"move": "e5"},
    )

    pgn_response = client.get(f"/games/{game_id}/pgn")

    assert pgn_response.status_code == 200
    assert "1. e4 e5" in pgn_response.text
    assert pgn_response.headers["content-type"].startswith(
        "application/x-chess-pgn"
    )

def test_bot_makes_a_legal_move():
    create_response = client.post("/games")
    game_id = create_response.json()["game_id"]

    client.post(
        f"/games/{game_id}/moves",
        json={"move": "e4"},
    )

    bot_response = client.post(f"/games/{game_id}/bot-move")

    assert bot_response.status_code == 200

    data = bot_response.json()

    assert data["bot_move"] is not None
    assert data["game"]["turn"] == "White"
    assert len(data["game"]["move_history"]) == 2

def test_human_move_triggers_bot_response():
    create_response = client.post("/games")
    game_id = create_response.json()["game_id"]

    response = client.post(
        f"/games/{game_id}/human-move",
        json={"move": "e4"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["human_move"] == "e4"
    assert data["bot_move"] is not None
    assert data["game"]["turn"] == "White"
    assert len(data["game"]["move_history"]) == 2

def test_create_easy_game():
    response = client.post("/games", json={"difficulty": "easy"})

    assert response.status_code == 200
    assert response.json()["game"]["difficulty"] == "easy"


def test_reject_invalid_difficulty():
    response = client.post("/games", json={"difficulty": "impossible"})

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Difficulty must be easy, medium, or hard"
    )