import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const START_FEN =
  "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

const PIECES = {
  K: "♔",
  Q: "♕",
  R: "♖",
  B: "♗",
  N: "♘",
  P: "♙",
  k: "♚",
  q: "♛",
  r: "♜",
  b: "♝",
  n: "♞",
  p: "♟",
};


function fenToSquares(fen) {
  const files = ["a", "b", "c", "d", "e", "f", "g", "h"];
  const ranks = fen.split(" ")[0].split("/");

  return ranks.flatMap((rank, rankIndex) => {
    const squares = [];
    let fileIndex = 0;

    for (const character of rank) {
      if (Number.isInteger(Number(character))) {
        for (let count = 0; count < Number(character); count += 1) {
          squares.push({
            square: `${files[fileIndex]}${8 - rankIndex}`,
            piece: null,
          });
          fileIndex += 1;
        }
      } else {
        squares.push({
          square: `${files[fileIndex]}${8 - rankIndex}`,
          piece: character,
        });
        fileIndex += 1;
      }
    }

    return squares;
  });
}

function App() {
  const [gameId, setGameId] = useState(null);
  const [game, setGame] = useState(null);
  const [difficulty, setDifficulty] = useState("medium");
  const [selectedSquare, setSelectedSquare] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [analysis, setAnalysis] = useState(null);
  

  const boardSquares = fenToSquares(game ? game.fen : START_FEN);

  const canMove =
    game &&
    !isLoading &&
    !game.is_game_over &&
    game.turn === "White";

  const legalTargets =
    selectedSquare && game
      ? new Set(
          game.legal_moves_uci
            .filter((move) => move.startsWith(selectedSquare))
            .map((move) => move.slice(2, 4)),
        )
      : new Set();

  function isWhitePiece(piece) {
    return piece && piece === piece.toUpperCase();
  }

  async function loadAnalysis(activeGameId) {
    try {
      const response = await fetch(
        `${API_URL}/games/${activeGameId}/analysis`,
      );

      if (!response.ok) {
        setAnalysis(null);
        return;
      }

      setAnalysis(await response.json());
    } catch {
      // Analysis is optional, so a failed request must not block the game.
      setAnalysis(null);
    }
  }

  async function startNewGame() {
    setIsLoading(true);
    setError("");
    setSelectedSquare(null);
    setAnalysis(null);

    try {
      const response = await fetch(`${API_URL}/games`, {
        method: "POST",
        headers: {
       "Content-Type": "application/json",
         },
  body: JSON.stringify({ difficulty }),
});

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not create a new game.");
      }

      setGameId(data.game_id);
      setGame(data.game);
      await loadAnalysis(data.game_id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function makeHumanMove(move) {
    setIsLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/games/${gameId}/human-move`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ move }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Move could not be played.");
      }

      setGame(data.game);
      await loadAnalysis(gameId);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSquareClick(square, piece) {
    if (!canMove) {
      return;
    }

    if (!selectedSquare) {
      if (isWhitePiece(piece)) {
        setSelectedSquare(square);
      }

      return;
    }

    if (isWhitePiece(piece)) {
      setSelectedSquare(square);
      return;
    }
    if (!legalTargets.has(square)) {
      setError("That move is not legal.");
      return;
    }

    let move = `${selectedSquare}${square}`;

    // Temporary rule: White pawn promotions automatically become queens.
    const selectedPiece = boardSquares.find(
  ({ square: boardSquare }) => boardSquare === selectedSquare,
)?.piece;

if (
  selectedPiece === "P" &&
  selectedSquare[1] === "7" &&
  square[1] === "8"
) {
  move += "q";
}

    setSelectedSquare(null);
    makeHumanMove(move);
  }

  return (
    <main className="app">
      <section className="game-layout">
        <div>
          <p className="eyebrow">ML Chess</p>
          <h1>Play against the bot</h1>


          <div className="chessboard">
            {boardSquares.map(({ square, piece }, index) => {
              const row = Math.floor(index / 8);
              const column = index % 8;
              const isDarkSquare = (row + column) % 2 === 1;
              const isSelected = selectedSquare === square;
              const isLegalTarget = legalTargets.has(square);

              return (
                <button
                  className={`square ${isDarkSquare ? "dark" : "light"} ${
  isSelected ? "selected" : ""
} ${isLegalTarget ? "legal-target" : ""}`}
                  disabled={!canMove}
                  key={square}
                  onClick={() => handleSquareClick(square, piece)}
                  type="button"
                >
                  <span className="piece">{piece ? PIECES[piece] : ""}</span>
                  {column === 0 && (
                    <span className="rank-label">{8 - row}</span>
                  )}
                  {row === 7 && (
                    <span className="file-label">
                      {["a", "b", "c", "d", "e", "f", "g", "h"][column]}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <aside className="side-panel">
        <label className="difficulty-selector">
  <span>Bot difficulty</span>
  <select
    value={difficulty}
    disabled={isLoading}
    onChange={(event) => setDifficulty(event.target.value)}
  >
    <option value="easy">Easy</option>
    <option value="medium">Medium</option>
    <option value="hard">Hard</option>
  </select>
</label>
          <button onClick={startNewGame} disabled={isLoading} type="button">
            {isLoading ? "Bot is thinking..." : "Start new game"}
          </button>

          {error && <p className="error">{error}</p>}

          {!game && (
            <p className="hint">
              Start a game. Then click a White piece, followed by its
              destination square.
            </p>
          )}

          {game && (
            <>
              <h2>
                {game.is_game_over
                  ? "Game over"
                  : isLoading
                    ? "Bot is thinking..."
                    : `${game.turn}'s turn`}
              </h2>

              <p className="difficulty-label">
  Difficulty: <strong>{game.difficulty}</strong>
</p>

              {game.is_game_over && (
                <p>
                  <strong>Result:</strong> {game.result}
                </p>
              )}

              <div className="moves">
                <h3>Move history</h3>
                <p>{game.move_history.join(" ") || "No moves yet."}</p>
              </div>

              {analysis && (
                <section className="analysis-panel">
                  <h3>ML thinking</h3>
                  <p className="analysis-value">
                    White position value: {analysis.expected_white_value >= 0 ? "+" : ""}
                    {analysis.expected_white_value.toFixed(2)}
                  </p>

                  <div className="outcome-probabilities">
                    {[
                      ["White win", "white_win"],
                      ["Draw", "draw"],
                      ["Black win", "black_win"],
                    ].map(([label, key]) => {
                      const probability = analysis.outcome_probabilities[key];

                      return (
                        <div className="outcome-row" key={key}>
                          <span>{label}</span>
                          <div className="probability-track">
                            <span
                              className={`probability-fill ${key}`}
                              style={{ width: `${probability * 100}%` }}
                            />
                          </div>
                          <strong>{(probability * 100).toFixed(1)}%</strong>
                        </div>
                      );
                    })}
                  </div>

                  <h4>Top candidate moves</h4>
                  <ol className="candidate-moves">
                    {analysis.top_moves.map((move) => (
                      <li key={move.uci}>{move.san}</li>
                    ))}
                  </ol>
                </section>
              )}

              <p className="hint">You play White. The bot plays Black.</p>
            </>
          )}
        </aside>
      </section>
    </main>
  );
}

export default App;
