from __future__ import annotations

import time
import random
import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

from ..game import Position, Move, generate_moves, apply_move, winner

EXACT = 0
LOWER = 1
UPPER = 2


@dataclass
class TTEntry:
    depth: int
    value: int
    flag: int
    best_move: Optional[Move]


TT: Dict[int, TTEntry] = {}
TT_MAX_SIZE = 200_000

NODES = 0
TT_HITS = 0
TT_STORES = 0


def reset_tt():
    global TT, NODES, TT_HITS, TT_STORES
    TT.clear()
    NODES = 0
    TT_HITS = 0
    TT_STORES = 0


_rng = random.Random(1337)
Z_PIECE = [[_rng.getrandbits(64) for _ in range(64)] for __ in range(2)]
Z_TURN = _rng.getrandbits(64)


def _stable_u64_from_obj(x: object) -> int:
    b = repr(x).encode("utf-8", errors="replace")
    return int.from_bytes(hashlib.blake2b(b, digest_size=8).digest(), "little", signed=False)


def _extract_ep_like_state(pos: Position) -> Optional[object]:
    for name in (
        "ep", "ep_sq", "ep_square", "en_passant", "en_passant_sq", "ep_target",
        "last_move", "last", "prev_move"
    ):
        if hasattr(pos, name):
            v = getattr(pos, name)
            if v is not None:
                return v
    return None


def zobrist_key(pos: Position) -> int:
    k = 0
    for sq in pos.white:
        k ^= Z_PIECE[0][sq]
    for sq in pos.black:
        k ^= Z_PIECE[1][sq]
    if pos.turn == "W":
        k ^= Z_TURN

    extra = _extract_ep_like_state(pos)
    if extra is not None:
        if isinstance(extra, Move):
            k ^= _stable_u64_from_obj(("lm", extra.src, extra.dst, int(getattr(extra, "is_ep", False))))
        elif isinstance(extra, int) and 0 <= extra < 64:
            k ^= _stable_u64_from_obj(("ep", extra))
        else:
            k ^= _stable_u64_from_obj(("extra", extra))

    return k


def _tt_maybe_evict():
    if len(TT) > TT_MAX_SIZE:
        TT.clear()


def _tt_store(key: int, depth: int, value: int, alpha0: int, beta0: int, best_move: Optional[Move]):
    global TT_STORES
    if value <= alpha0:
        flag = UPPER
    elif value >= beta0:
        flag = LOWER
    else:
        flag = EXACT

    old = TT.get(key)
    if old is None or depth >= old.depth:
        TT[key] = TTEntry(depth=depth, value=value, flag=flag, best_move=best_move)
        TT_STORES += 1
        _tt_maybe_evict()


def _tt_probe(key: int, depth: int, alpha: int, beta: int) -> Tuple[bool, int, int, Optional[int]]:
    global TT_HITS
    entry = TT.get(key)
    if entry is None or entry.depth < depth:
        return (False, alpha, beta, None)

    TT_HITS += 1

    if entry.flag == EXACT:
        return (True, alpha, beta, entry.value)

    if entry.flag == LOWER:
        alpha = max(alpha, entry.value)
    elif entry.flag == UPPER:
        beta = min(beta, entry.value)

    if alpha >= beta:
        return (True, alpha, beta, entry.value)

    return (True, alpha, beta, None)


def apply_move_fixed(pos: Position, mv: Move) -> Position:
    mover = pos.turn
    new_pos = apply_move(pos, mv)

    # EP manual fix
    try:
        if getattr(mv, "is_ep", False):
            cap_sq = mv.dst - 8 if mover == "W" else mv.dst + 8
            if mover == "W":
                try:
                    new_pos.black.discard(cap_sq)
                except Exception:
                    pass
            else:
                try:
                    new_pos.white.discard(cap_sq)
                except Exception:
                    pass
    except Exception:
        pass

    # attach last_move for TT correctness
    try:
        setattr(new_pos, "last_move", mv)
    except Exception:
        pass

    return new_pos


def evaluate(pos: Position) -> int:
    w = len(pos.white)
    b = len(pos.black)
    w_prog = sum(((sq >> 3) + 1) for sq in pos.white)
    b_prog = sum((9 - ((sq >> 3) + 1)) for sq in pos.black)
    return 100 * (w - b) + 3 * (w_prog - b_prog)


def _is_capture(pos: Position, mv: Move) -> bool:
    opp = pos.black if pos.turn == "W" else pos.white
    return mv.is_ep or (mv.dst in opp)


def compute_time_budget(time_left_sec: Optional[float]) -> float:
    """
    Allocate a per-move budget from the TOTAL remaining game time.

    Conservative + safe:
    - keep a reserve so we don't lose on timeout
    - scale by remaining time and "game complexity"
    """
    if time_left_sec is None:
        return 0.15  # fallback (your old default)

    # Safety reserve: never spend the last ~50ms
    reserve = 0.05
    tl = max(0.0, time_left_sec - reserve)

    # Spend about 1/35 of remaining time, clamped.
    # (So if 10s left => ~0.285s, but clamp it)
    budget = tl / 35.0
    return max(0.02, min(0.35, budget))


def choose_move_iterdeep(
    pos: Position,
    time_left_sec: Optional[float] = None,
    max_depth: int = 64
) -> Move:
    budget = compute_time_budget(time_left_sec)

    start = time.perf_counter()
    deadline = start + budget

    best: Optional[Move] = None
    depth = 1

    global NODES
    NODES = 0

    while depth <= max_depth:
        if time.perf_counter() >= deadline:
            break
        mv, _ = _search_depth(pos, depth, deadline)
        if mv is not None:
            best = mv
        depth += 1

    if best is None:
        moves = list(generate_moves(pos))
        if not moves:
            raise RuntimeError("No legal moves.")
        return moves[0]
    return best


def _search_depth(pos: Position, depth: int, deadline: float) -> Tuple[Optional[Move], int]:
    maximizing = (pos.turn == "W")
    best_mv: Optional[Move] = None
    best_val = -10**18 if maximizing else 10**18

    moves = list(generate_moves(pos))
    if not moves:
        return None, evaluate(pos)

    moves.sort(key=lambda m: 1 if _is_capture(pos, m) else 0, reverse=True)

    key = zobrist_key(pos)
    entry = TT.get(key)
    if entry is not None and entry.best_move is not None and entry.best_move in moves:
        moves.remove(entry.best_move)
        moves.insert(0, entry.best_move)

    alpha, beta = -10**18, 10**18
    alpha0, beta0 = alpha, beta

    for mv in moves:
        if time.perf_counter() >= deadline:
            break

        val = _alphabeta(apply_move_fixed(pos, mv), depth - 1, alpha, beta, deadline)

        if maximizing:
            if val > best_val:
                best_val, best_mv = val, mv
            alpha = max(alpha, best_val)
        else:
            if val < best_val:
                best_val, best_mv = val, mv
            beta = min(beta, best_val)

        if beta <= alpha:
            break

    _tt_store(key, depth, best_val, alpha0, beta0, best_mv)
    return best_mv, best_val


def _alphabeta(pos: Position, depth: int, alpha: int, beta: int, deadline: float) -> int:
    global NODES
    NODES += 1

    if time.perf_counter() >= deadline:
        return evaluate(pos)

    w = winner(pos)
    if w is not None:
        return 10**12 if w == "W" else -10**12

    if depth <= 0:
        return evaluate(pos)

    key = zobrist_key(pos)
    alpha0, beta0 = alpha, beta
    _, alpha, beta, exact_val = _tt_probe(key, depth, alpha, beta)
    if exact_val is not None:
        return exact_val

    maximizing = (pos.turn == "W")
    moves = list(generate_moves(pos))
    if not moves:
        return evaluate(pos)

    moves.sort(key=lambda m: 1 if _is_capture(pos, m) else 0, reverse=True)
    entry = TT.get(key)
    if entry is not None and entry.best_move is not None and entry.best_move in moves:
        moves.remove(entry.best_move)
        moves.insert(0, entry.best_move)

    best_move: Optional[Move] = None

    if maximizing:
        v = -10**18
        for mv in moves:
            if time.perf_counter() >= deadline:
                break
            child = _alphabeta(apply_move_fixed(pos, mv), depth - 1, alpha, beta, deadline)
            if child > v:
                v = child
                best_move = mv
            alpha = max(alpha, v)
            if beta <= alpha:
                break
        _tt_store(key, depth, v, alpha0, beta0, best_move)
        return v
    else:
        v = 10**18
        for mv in moves:
            if time.perf_counter() >= deadline:
                break
            child = _alphabeta(apply_move_fixed(pos, mv), depth - 1, alpha, beta, deadline)
            if child < v:
                v = child
                best_move = mv
            beta = min(beta, v)
            if beta <= alpha:
                break
        _tt_store(key, depth, v, alpha0, beta0, best_move)
        return v
