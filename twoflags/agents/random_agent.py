from __future__ import annotations
import random
from typing import Optional
from ..game import Position, Move, generate_moves

def choose_move(pos: Position, rng: Optional[random.Random] = None) -> Move:
    rng = rng or random.Random()
    moves = list(generate_moves(pos))
    if not moves:
        raise RuntimeError("No legal moves.")
    return rng.choice(moves)
