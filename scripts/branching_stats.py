from __future__ import annotations

import argparse
import math
import random
import time
from typing import List, Tuple

from twoflags.game import Position, generate_moves, apply_move
import twoflags.agents.ab_agent as ab


def random_position(random_plies: int, rng: random.Random) -> Position:
    """Start from initial position and play random legal moves for random_plies plies."""
    pos = Position.initial()
    for _ in range(random_plies):
        moves = list(generate_moves(pos))
        if not moves:
            break
        mv = rng.choice(moves)
        pos = apply_move(pos, mv)
    return pos


def solve_effective_branching_factor(nodes: int, depth: int) -> float:
    """
    Solve for b in: N ≈ 1 + b + b^2 + ... + b^depth  (uniform tree approximation)
    using binary search. Returns b.

    Notes:
    - Our node counter typically does not include the root, so we use nodes+1.
    """
    if depth <= 0:
        return 0.0
    N = max(1, nodes + 1)

    # If N is extremely small, branching is ~1
    if N <= depth + 1:
        return 1.0

    def series(b: float) -> float:
        # (b^(d+1)-1)/(b-1)
        return (b ** (depth + 1) - 1.0) / (b - 1.0)

    lo, hi = 1.000001, 200.0
    # Ensure hi is high enough
    while series(hi) < N:
        hi *= 2.0
        if hi > 1e6:
            break

    for _ in range(60):
        mid = (lo + hi) / 2.0
        if series(mid) < N:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def run_agent_one_move_stats(pos: Position, budget: float, max_depth: int, keep_tt: bool) -> Tuple[int, int]:
    """
    Run one iterative-deepening move search and return:
      (reached_depth, nodes_expanded)

    We reproduce the outer iterative-deepening loop so we can measure depth+nodes
    without changing your agent code.
    """
    if not keep_tt:
        ab.reset_tt()

    ab.NODES = 0  # reset per-move node counter

    start = time.time()
    depth = 1
    best = None

    while depth <= max_depth:
        if time.time() - start > budget:
            break

        mv, _val = ab._search_depth(pos, depth, start, budget)
        if mv is not None:
            best = mv

        depth += 1

    reached_depth = depth - 1
    nodes = ab.NODES

    # If best is None, that usually means no legal moves / terminal; still return stats
    return reached_depth, nodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--random-plies", type=int, default=8)
    ap.add_argument("--budget", type=float, default=0.15, help="seconds per move for stats run")
    ap.add_argument("--max-depth", type=int, default=64)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--keep-tt", action="store_true", help="keep TT across samples (closer to real game)")
    args = ap.parse_args()

    rng = random.Random(args.seed)

    b_game: List[int] = []
    depths: List[int] = []
    nodes_list: List[int] = []
    ebf_list: List[float] = []

    t0 = time.time()

    for _ in range(args.samples):
        pos = random_position(args.random_plies, rng)

        # C(e): game branching factor at this position
        moves = list(generate_moves(pos))
        b_game.append(len(moves))

        # C(f): agent effective branching factor for this position
        d, nodes = run_agent_one_move_stats(pos, args.budget, args.max_depth, args.keep_tt)
        depths.append(d)
        nodes_list.append(nodes)

        if d > 0 and nodes > 0:
            ebf = solve_effective_branching_factor(nodes, d)
            ebf_list.append(ebf)

    dt = time.time() - t0

    def avg(xs):
        return sum(xs) / max(1, len(xs))

    print("=== Branching Factor Stats ===")
    print(f"Samples: {args.samples}")
    print(f"Random plies before sampling: {args.random_plies}")
    print(f"Budget per move (stats run): {args.budget:.3f}s")
    print(f"Max depth cap: {args.max_depth}")
    print(f"TT kept across samples: {args.keep_tt}")
    print(f"Runtime: {dt:.2f}s\n")

    print("Game branching factor (legal moves per position):")
    print(f"  min: {min(b_game)}")
    print(f"  avg: {avg(b_game):.2f}")
    print(f"  max: {max(b_game)}\n")

    print("Search depth reached in stats runs:")
    print(f"  min depth: {min(depths)}")
    print(f"  avg depth: {avg(depths):.2f}")
    print(f"  max depth: {max(depths)}\n")

    print("[Nodes expanded per move-search]:")
    print(f"  min nodes: {min(nodes_list)}")
    print(f"  avg nodes: {avg(nodes_list):.2f}")
    print(f"  max nodes: {max(nodes_list)}\n")

    print("Effective branching factor (agent):")
    if ebf_list:
        print(f"  min ebf: {min(ebf_list):.2f}")
        print(f"  avg ebf: {avg(ebf_list):.2f}")
        print(f"  max ebf: {max(ebf_list):.2f}")
        print("  (Computed by solving: N ≈ 1 + b + ... + b^d)")
    else:
        print("  Not enough data to compute (depth/nodes too small).")


if __name__ == "__main__":
    main()
