from typing import List, Optional

WIN_LINES = [
    (0,1,2),(3,4,5),(6,7,8),
    (0,3,6),(1,4,7),(2,5,8),
    (0,4,8),(2,4,6)
]

class TicTacToe:
    def __init__(self):
        self.board: List[str] = [' '] * 9
        self.turn: str = 'X'  # X always starts
        self.winner: Optional[str] = None
        self.moves = 0

    def make_move(self, idx: int, sym: str) -> bool:
        if self.board[idx] is not None and self.board[idx] != ' ' or self.winner is not None:
            return False
        if sym != self.turn:
            return False
        self.board[idx] = sym
        self.moves += 1
        self._check_winner()
        if self.winner is None:
            self.turn = 'O' if self.turn == 'X' else 'X'
        return True

    def _check_winner(self):
        for a,b,c in WIN_LINES:
            if self.board[a] == self.board[b] == self.board[c] != ' ':
                self.winner = self.board[a]
                return
        if self.moves >= 9:
            self.winner = 'T'  # tie

    def as_dict(self):
        return {'board': self.board, 'turn': self.turn, 'winner': self.winner}

    def printable(self):
        b = self.board
        lines = [f" {b[0]} | {b[1]} | {b[2]} ", "-----------", f" {b[3]} | {b[4]} | {b[5]} ", "-----------", f" {b[6]} | {b[7]} | {b[8]} "]
        return '\n'.join(lines)