#!/usr/bin/env python3
"""
chess_game.py - state and rules for the playable board on the profile README.

Visitors play by opening an issue titled `chess|move|e2e4`. The workflow calls

  python chess_game.py            (reads ISSUE_TITLE and ISSUE_USER from the environment)

which validates the move with python-chess, updates chess/game.json and prints
a one-line reply for the issue. Exit code 0 means the board changed, 2 means
the request was rejected and nothing was written.
"""

import json
import os
import re
import sys

import chess

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "chess", "game.json")

TITLE_RE = re.compile(r"^chess\|(?:move\|([a-h][1-8][a-h][1-8][qrbn]?)|(new))$")
USER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\[bot\])?$")
PIECE_NAMES = {
    chess.PAWN: "Pawn", chess.KNIGHT: "Knight", chess.BISHOP: "Bishop",
    chess.ROOK: "Rook", chess.QUEEN: "Queen", chess.KING: "King",
}
# A new game may only be forced once this many moves have been played.
MIN_MOVES_BEFORE_RESET = 20


def new_state(finished=0, last_result=None):
    return {"fen": chess.STARTING_FEN, "history": [], "finished": finished,
            "last_result": last_result}


def load_state():
    if not os.path.exists(STATE):
        return new_state()
    with open(STATE, encoding="utf-8") as fh:
        return json.load(fh)


def save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")


def describe_end(board):
    outcome = board.outcome(claim_draw=True)
    reason = outcome.termination.name.replace("_", " ").lower()
    if outcome.winner is None:
        return f"Draw by {reason}"
    return f"{'White' if outcome.winner else 'Black'} won by {reason}"


def apply_move(state, uci, user):
    """Play `uci` on the stored position. Returns (state, reply). Raises ValueError."""
    board = chess.Board(state["fen"])
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves:
        side = "White" if board.turn else "Black"
        raise ValueError(f"`{uci}` is not a legal move here. It is {side}'s turn; "
                         "pick one of the moves listed on the profile.")
    san = board.san(move)
    color = "White" if board.turn else "Black"
    number = board.fullmove_number
    board.push(move)
    state["history"].append({"n": number, "color": color, "san": san, "uci": uci, "by": user})
    state["fen"] = board.fen()
    if board.is_game_over(claim_draw=True):
        result = f"{describe_end(board)} after {len(state['history'])} moves"
        state = new_state(finished=state.get("finished", 0) + 1, last_result=result)
        return state, f"{color} played **{san}**. {result}. A new game has started."
    return state, f"{color} played **{san}**. The board is updated; thanks for playing."


def handle(title, user):
    """Returns (exit_code, reply)."""
    match = TITLE_RE.match(title.strip())
    if not match:
        return 2, "That title is not a chess command. Use the move links on the profile."
    if not USER_RE.match(user):
        return 2, "Could not read the account that opened this issue."
    state = load_state()
    if match.group(2):
        played = len(state["history"])
        if played < MIN_MOVES_BEFORE_RESET:
            return 2, (f"A new game can be started after {MIN_MOVES_BEFORE_RESET} moves; "
                       f"this one has {played}.")
        save_state(new_state(finished=state.get("finished", 0) + 1,
                             last_result=f"Game restarted after {played} moves"))
        return 0, "A new game has started. White to move."
    try:
        state, reply = apply_move(state, match.group(1), user)
    except ValueError as err:
        return 2, str(err)
    save_state(state)
    return 0, reply


def view(state):
    """Everything the README needs: turn, last move squares and grouped legal moves."""
    board = chess.Board(state["fen"])
    last = state["history"][-1]["uci"] if state["history"] else None
    groups = {}
    for move in sorted(board.legal_moves, key=lambda m: (m.from_square, m.to_square, m.promotion or 0)):
        piece = board.piece_at(move.from_square)
        key = (PIECE_NAMES[piece.piece_type], chess.square_name(move.from_square))
        groups.setdefault(key, []).append((board.san(move), move.uci()))
    return {
        "placement": board.board_fen(),
        "turn": "White" if board.turn else "Black",
        "check": board.is_check(),
        "last": (last[:2], last[2:4]) if last else None,
        "moves": [(piece, square, options) for (piece, square), options in groups.items()],
        "history": state["history"],
        "finished": state.get("finished", 0),
        "last_result": state.get("last_result"),
        "can_reset": len(state["history"]) >= MIN_MOVES_BEFORE_RESET,
    }


def main():
    code, reply = handle(os.environ.get("ISSUE_TITLE", ""), os.environ.get("ISSUE_USER", ""))
    print(reply)
    sys.exit(code)


if __name__ == "__main__":
    main()
