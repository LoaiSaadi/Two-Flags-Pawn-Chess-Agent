# bonus/tlog.py
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

MOVE_RE = re.compile(r'^\[MOVE\]\s+ply=(\d+)\s+(WHITE|BLACK)\s+->\s+([a-h][1-8])([a-h][1-8])\s*$')
GAME_RE = re.compile(r'^\[GAME\s+(\d+)\]\s+white=(\S+)\s+black=(\S+)\s*$')
END_RE  = re.compile(r'^\[END\]\s+RESIGNATION\s+by\s+(WHITE|BLACK)\s+at\s+ply\s+(\d+)\s+\|\s+winner=(WHITE|BLACK)\s*$')

FILES = "abcdefgh"

def sq_to_xy(sq: str) -> Tuple[int, int]:
    # a1 -> (0,0), h8 -> (7,7)
    f = FILES.index(sq[0])
    r = int(sq[1]) - 1
    return f, r

def xy_to_sq(x: int, y: int) -> str:
    return f"{FILES[x]}{y+1}"

def is_promo_square(side: str, sq: str) -> bool:
    # Side is "WHITE" or "BLACK"
    rank = int(sq[1])
    return (side == "WHITE" and rank == 8) or (side == "BLACK" and rank == 1)

@dataclass
class Move:
    ply: int
    side: str   # "WHITE" or "BLACK"
    frm: str
    to: str

@dataclass
class Game:
    gid: int
    white_player: str
    black_player: str
    moves: List[Move] = field(default_factory=list)
    resign_by: Optional[str] = None     # "WHITE"/"BLACK"
    winner_side: Optional[str] = None   # "WHITE"/"BLACK"
    end_ply: Optional[int] = None

def parse_tournament_log(path: str) -> List[Game]:
    games: List[Game] = []
    cur: Optional[Game] = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")

            m = GAME_RE.match(line)
            if m:
                if cur is not None:
                    games.append(cur)
                cur = Game(gid=int(m.group(1)), white_player=m.group(2), black_player=m.group(3))
                continue

            m = MOVE_RE.match(line)
            if m and cur is not None:
                cur.moves.append(Move(
                    ply=int(m.group(1)),
                    side=m.group(2),
                    frm=m.group(3),
                    to=m.group(4),
                ))
                continue

            m = END_RE.match(line)
            if m and cur is not None:
                cur.resign_by = m.group(1)
                cur.end_ply = int(m.group(2))
                cur.winner_side = m.group(3)
                # keep cur open until next GAME or EOF
                continue

    if cur is not None:
        games.append(cur)

    # Drop any incomplete games that never ended (optional)
    games = [g for g in games if g.winner_side is not None]
    return games

# --------------------------
# Minimal pawn-only board
# --------------------------
class PawnBoard:
    """
    Assumes standard pawn starts:
      White pawns: a2..h2
      Black pawns: a7..h7
    Supports:
      - forward 1/2
      - diagonal capture
      - basic en-passant heuristic (optional)
    Enough for trajectory visualization & opening stats.
    """
    def __init__(self):
        self.occ: Dict[str, Tuple[str, str]] = {}  # sq -> (side, pawn_id)
        self.paths: Dict[str, List[str]] = defaultdict(list)
        self.last_move: Optional[Tuple[str, str, str]] = None  # (side, frm, to)

        # init pawns
        for x, f in enumerate(FILES):
            w = f"{f}2"
            b = f"{f}7"
            wid = f"W_{w}"
            bid = f"B_{b}"
            self.occ[w] = ("WHITE", wid)
            self.occ[b] = ("BLACK", bid)
            self.paths[wid].append(w)
            self.paths[bid].append(b)

    def _remove(self, sq: str):
        if sq in self.occ:
            del self.occ[sq]

    def apply(self, mv: Move):
        side = mv.side
        frm, to = mv.frm, mv.to

        if frm not in self.occ:
            # If your engine ever changes piece types on promotion etc.,
            # this can happen. We just ignore to keep analysis running.
            self.last_move = (side, frm, to)
            return

        occ_side, pid = self.occ[frm]
        if occ_side != side:
            self.last_move = (side, frm, to)
            return

        # Capture if destination occupied by opponent
        if to in self.occ and self.occ[to][0] != side:
            self._remove(to)

        # En-passant heuristic: diagonal move to empty square
        fx, fy = sq_to_xy(frm)
        tx, ty = sq_to_xy(to)
        if (to not in self.occ) and (abs(tx - fx) == 1):
            # white captures "up", black captures "down"
            if side == "WHITE" and (ty - fy) == 1:
                captured_sq = xy_to_sq(tx, fy)  # e.g., f5->e6 captures e5
                self._remove(captured_sq)
            if side == "BLACK" and (fy - ty) == 1:
                captured_sq = xy_to_sq(tx, fy)  # e.g., e4->f3 captures f4
                self._remove(captured_sq)

        # Move pawn
        self._remove(frm)
        self.occ[to] = (side, pid)
        self.paths[pid].append(to)

        self.last_move = (side, frm, to)

def compute_elo_from_games(games: List[Game], client1: str, client2: str, baseline=1500.0, k=40.0):
    """
    Returns final (r1,r2), plus win stats.
    """
    r = {client1: baseline, client2: baseline}
    w = {client1: 0.0, client2: 0.0}
    n = 0

    for g in games:
        # map winner side -> player name
        if g.winner_side == "WHITE":
            winner = g.white_player
        else:
            winner = g.black_player

        if winner not in r:
            # ignore games with unexpected player names
            continue

        loser = client2 if winner == client1 else client1
        n += 1
        w[winner] += 1.0

        ra, rb = r[client1], r[client2]
        ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))
        eb = 1.0 - ea

        sa = 1.0 if winner == client1 else 0.0
        sb = 1.0 - sa

        r[client1] = ra + k * (sa - ea)
        r[client2] = rb + k * (sb - eb)

    return r[client1], r[client2], w[client1], w[client2], n
