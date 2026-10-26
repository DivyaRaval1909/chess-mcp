from chess_game import ChessGame

game = ChessGame()

print("Welcome to Chess!")
print("Enter moves such as: e4, Nf3, O-O")
print("Commands:")
print("  history             Show moves played")
print("  pgn                 Show PGN notation")
print("  save my_game.pgn    Save the current game")
print("  load my_game.pgn    Load a saved game")
print("  quit                Exit the game\n")

while not game.is_game_over():
    print(game.board)
    print()

    move_text = input(f"{game.current_player()}'s move: ").strip()

    if move_text.lower() == "quit":
        print("Game ended by user.")
        break

    if move_text.lower() == "history":
        print("\nMoves played:")
        print(game.get_history())
        print()
        continue

    if move_text.lower() == "pgn":
        print("\nPGN export:")
        print(game.get_pgn())
        print()
        continue

    if move_text.lower().startswith("save "):
        file_path = move_text[5:].strip()

        if not file_path:
            print("Please provide a filename, for example: save my_game.pgn\n")
            continue

        game.save_pgn(file_path)
        print(f"Game saved to: {file_path}\n")
        continue

    if move_text.lower().startswith("load "):
        file_path = move_text[5:].strip()

        if not file_path:
            print("Please provide a filename, for example: load my_game.pgn\n")
            continue

        try:
            game = ChessGame.load_pgn(file_path)
            print(f"Game loaded from: {file_path}\n")
        except FileNotFoundError:
            print(f"File not found: {file_path}\n")
        except ValueError as error:
            print(f"Could not load game: {error}\n")

        continue

    try:
        game.play_move(move_text)
    except ValueError:
        print("Invalid or illegal move. Try again.\n")

print("\nFinal board:")
print(game.board)

if game.is_game_over():
    print("\nGame over!")
    print("Result:", game.get_result())

print("\nFinal PGN:")
print(game.get_pgn())