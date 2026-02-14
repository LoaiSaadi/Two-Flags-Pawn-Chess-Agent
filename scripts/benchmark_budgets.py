from __future__ import annotations

import argparse
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from twoflags.game import Position, apply_move, winner, generate_moves
from twoflags.agents.ab_agent import choose_move_iterdeep
from twoflags.agents.random_agent import choose_move as choose_random_move


@dataclass
class Result:
    games: int = 0
    bench_wins: int = 0
    bench_losses: int = 0
    draws: int = 0
    total_plies: int = 0
    wall_time_sec: float = 0.0


def play_game(
    budget_white: float,
    budget_black: float,
    rng: random.Random,
    opening_random_plies: int = 2,
    max_plies: int = 500,
) -> Tuple[Optional[str], int]:
    """
    Returns (winner_color or None, plies_played).
    Winner_color is 'W' or 'B'.
    """
    pos = Position.initial()

    for ply in range(max_plies):
        w = winner(pos)
        if w is not None:
            return w, ply

        # Small randomized opening to create variety
        if ply < opening_random_plies:
            mv = choose_random_move(pos, rng=rng)
        else:
            budget = budget_white if pos.turn == "W" else budget_black
            mv = choose_move_iterdeep(pos, time_budget_sec=budget)

        pos = apply_move(pos, mv)

    # Shouldn't happen in this pawn game, but keep it safe:
    return None, max_plies


def run_benchmark(
    budgets: List[float],
    baseline: float,
    games: int,
    opening_random_plies: int,
    seed: int,
) -> None:
    rng = random.Random(seed)

    print("\nBenchmark setup")
    print(f"  games per budget: {games} (half as W, half as B)")
    print(f"  baseline budget:  {baseline:.3f}s per move")
    print(f"  opening plies:    {opening_random_plies} (random)")
    print(f"  seed:             {seed}")
    print("\nResults (bench = agent with tested budget)\n")

    header = f"{'budget(s)':>9} | {'W%':>6} | {'L%':>6} | {'D%':>6} | {'avg plies':>9} | {'wall(s)':>7}"
    print(header)
    print("-" * len(header))

    for b in budgets:
        res = Result()
        t0 = time.time()

        for i in range(games):
            # Alternate colors to reduce first-move advantage:
            # even i: bench plays White; odd i: bench plays Black
            if i % 2 == 0:
                w, plies = play_game(
                    budget_white=b,
                    budget_black=baseline,
                    rng=rng,
                    opening_random_plies=opening_random_plies,
                )
                bench_color = "W"
            else:
                w, plies = play_game(
                    budget_white=baseline,
                    budget_black=b,
                    rng=rng,
                    opening_random_plies=opening_random_plies,
                )
                bench_color = "B"

            res.games += 1
            res.total_plies += plies

            if w is None:
                res.draws += 1
            elif w == bench_color:
                res.bench_wins += 1
            else:
                res.bench_losses += 1

        res.wall_time_sec = time.time() - t0

        w_pct = 100.0 * res.bench_wins / res.games
        l_pct = 100.0 * res.bench_losses / res.games
        d_pct = 100.0 * res.draws / res.games
        avg_plies = res.total_plies / res.games

        print(f"{b:9.3f} | {w_pct:6.1f} | {l_pct:6.1f} | {d_pct:6.1f} | {avg_plies:9.1f} | {res.wall_time_sec:7.1f}")

    print("\nTip: If W% increases as budget increases, alpha-beta is benefiting from deeper search.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20, help="games per budget (alternating colors)")
    ap.add_argument("--baseline", type=float, default=0.05, help="baseline opponent budget (seconds per move)")
    ap.add_argument("--opening", type=int, default=2, help="random opening plies to add variety (0 disables)")
    ap.add_argument("--seed", type=int, default=123, help="random seed")
    ap.add_argument("--budgets", type=float, nargs="+", default=[0.05, 0.1, 0.2, 0.5], help="budgets to test (seconds per move)")
    args = ap.parse_args()

    run_benchmark(
        budgets=args.budgets,
        baseline=args.baseline,
        games=args.games,
        opening_random_plies=args.opening,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
