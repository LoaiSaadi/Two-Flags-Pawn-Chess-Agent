from __future__ import annotations

import re
from typing import List

from .game import Position, Move, FILES, sq_index, file_of, rank_of, generate_moves

_SQ_RE = re.compile(r"^[a-h][1-8]$|^[1-8][a-h]$", re.IGNORECASE)

def parse_square(token: str) -> int:
    t = token.strip().lower()
    if not _SQ_RE.match(t):
        raise ValueError(f"Bad square token: {token!r}")
    if t[0].isalpha():  # a2
        file_ch, rank_ch = t[0], t[1]
    else:               # 2a
        rank_ch, file_ch = t[0], t[1]
    return sq_index(FILES.index(file_ch), int(rank_ch))

def square_to_fr(sq: int) -> str:
    return f"{FILES[file_of(sq)]}{rank_of(sq)}"

def move_to_str_fr(mv: Move) -> str:
    return square_to_fr(mv.src) + square_to_fr(mv.dst)

def parse_setup(tokens: List[str]) -> Position:
    if not tokens or tokens[0].lower() != "setup":
        raise ValueError("setup must start with 'Setup'")
    w, b = set(), set()
    for tok in tokens[1:]:
        t = tok.strip()
        if len(t) != 3:
            raise ValueError(f"Bad setup token: {tok!r}")
        col = t[0].upper()
        sq = parse_square(t[1:3])
        (w if col == "W" else b if col == "B" else None)
        if col == "W":
            w.add(sq)
        elif col == "B":
            b.add(sq)
        else:
            raise ValueError(f"Bad color in setup token: {tok!r}")
    return Position(white=w, black=b, turn="W", ep_target=None)

def parse_move_robust(s: str, pos: Position) -> Move:
    raw = s.strip().lower().replace("->", "").replace("-", "").replace(" ", "")
    if len(raw) != 4:
        raise ValueError(f"Bad move string: {s!r}")
    a, b = raw[:2], raw[2:]
    cands = [(parse_square(a), parse_square(b)), (parse_square(b), parse_square(a))]
    legal = {(m.src, m.dst, m.is_ep, m.is_double) for m in generate_moves(pos)}
    for src, dst in cands:
        for (lsrc, ldst, lep, ldbl) in legal:
            if lsrc == src and ldst == dst:
                return Move(src, dst, is_ep=lep, is_double=ldbl)
    raise ValueError(f"Illegal move {s!r} for current position.")
