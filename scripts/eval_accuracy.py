from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from twoflags.game import Position, apply_move, generate_moves, winner
from twoflags.agents.ab_agent import evaluate


# ----------------------------
# Helpers
# ----------------------------
def outcome_value(w: Optional[str]) -> int:
    """
    Map terminal winner to numeric label from WHITE perspective:
      WHITE win -> +1
      BLACK win -> -1
      None / draw / unknown -> 0
    """
    if w is None:
        return 0
    w = w.upper()
    if w == "W":
        return +1
    if w == "B":
        return -1
    return 0


def play_random_to_end(pos: Position, rng: random.Random, max_plies: int) -> int:
    """
    Play a random game from pos until terminal (or max_plies).
    Returns +1 if White wins, -1 if Black wins, 0 otherwise.
    """
    p = pos
    for _ in range(max_plies):
        w = winner(p)
        if w is not None:
            return outcome_value(w)

        moves = list(generate_moves(p))
        if not moves:
            # no legal moves; treat as terminal if winner() didn't
            return outcome_value(winner(p))

        mv = rng.choice(moves)
        p = apply_move(p, mv)

    # hit ply cap: treat as draw/unknown
    return 0


def randomize_position(rng: random.Random, random_plies: int) -> Position:
    """
    Start from initial position and play 'random_plies' random half-moves.
    """
    p = Position.initial()
    for _ in range(random_plies):
        w = winner(p)
        if w is not None:
            break
        moves = list(generate_moves(p))
        if not moves:
            break
        p = apply_move(p, rng.choice(moves))
    return p


def spearman_rank_corr(xs: List[float], ys: List[float]) -> float:
    """
    Spearman correlation without external libs.
    """
    if len(xs) != len(ys) or len(xs) < 2:
        return float("nan")

    def rank(a: List[float]) -> List[float]:
        # average ranks for ties
        sorted_idx = sorted(range(len(a)), key=lambda i: a[i])
        r = [0.0] * len(a)
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[sorted_idx[j + 1]] == a[sorted_idx[i]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[sorted_idx[k]] = avg_rank
            i = j + 1
        return r

    rx = rank(xs)
    ry = rank(ys)

    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    denx = math.sqrt(sum((rx[i] - mx) ** 2 for i in range(len(rx))))
    deny = math.sqrt(sum((ry[i] - my) ** 2 for i in range(len(ry))))
    if denx == 0 or deny == 0:
        return float("nan")
    return num / (denx * deny)


@dataclass
class SampleResult:
    eval_score: int
    white_win_rate: float
    avg_outcome: float  # in [-1, +1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=150, help="How many positions to sample")
    ap.add_argument("--rollouts", type=int, default=30, help="Random playouts per sampled position")
    ap.add_argument("--random-plies", type=int, default=6, help="Randomize this many plies before sampling")
    ap.add_argument("--max-plies", type=int, default=200, help="Max plies per rollout game")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    rng = random.Random(args.seed)

    results: List[SampleResult] = []

    for _ in range(args.samples):
        pos = randomize_position(rng, args.random_plies)
        s = int(evaluate(pos))

        outcomes = [play_random_to_end(pos, rng, args.max_plies) for _ in range(args.rollouts)]
        white_wins = sum(1 for o in outcomes if o == +1)
        black_wins = sum(1 for o in outcomes if o == -1)
        draws = sum(1 for o in outcomes if o == 0)

        ww_rate = white_wins / args.rollouts
        avg_out = sum(outcomes) / args.rollouts  # in [-1, +1]

        results.append(SampleResult(eval_score=s, white_win_rate=ww_rate, avg_outcome=avg_out))

    # --- Metrics ---
    evals = [r.eval_score for r in results]
    winrates = [r.white_win_rate for r in results]
    avg_outcomes = [r.avg_outcome for r in results]

    # Sign accuracy: does sign(eval) match sign(avg_outcome)?
    # ignore near-zero evals to avoid noisy claims
    eps = 1  # threshold for "non-zero"
    usable = [r for r in results if abs(r.eval_score) >= eps]
    if usable:
        correct = 0
        for r in usable:
            pred = 1 if r.eval_score > 0 else -1
            true = 1 if r.avg_outcome > 0 else (-1 if r.avg_outcome < 0 else 0)
            if true != 0 and pred == true:
                correct += 1
        sign_acc = correct / max(1, sum(1 for r in usable if r.avg_outcome != 0))
    else:
        sign_acc = float("nan")

    sp1 = spearman_rank_corr([float(x) for x in evals], winrates)
    sp2 = spearman_rank_corr([float(x) for x in evals], avg_outcomes)

    print("=== Evaluation Accuracy Experiment ===")
    print(f"Samples: {args.samples}")
    print(f"Rollouts per sample: {args.rollouts}")
    print(f"Random plies before sampling: {args.random_plies}")
    print(f"Max plies per rollout: {args.max_plies}")
    print(f"Seed: {args.seed}")
    print()
    print(f"Sign accuracy (ignoring |eval|<{eps}): {sign_acc:.3f}")
    print(f"Spearman corr(eval, white_win_rate): {sp1:.3f}")
    print(f"Spearman corr(eval, avg_outcome):   {sp2:.3f}")

    # Simple bucket summary
    results_sorted = sorted(results, key=lambda r: r.eval_score)
    buckets = 5
    print("\nBucket summary (by eval score):")
    for bi in range(buckets):
        lo = bi * len(results_sorted) // buckets
        hi = (bi + 1) * len(results_sorted) // buckets
        chunk = results_sorted[lo:hi]
        if not chunk:
            continue
        avg_eval = sum(r.eval_score for r in chunk) / len(chunk)
        avg_wr = sum(r.white_win_rate for r in chunk) / len(chunk)
        avg_out = sum(r.avg_outcome for r in chunk) / len(chunk)
        print(f"  Bucket {bi+1}: avg_eval={avg_eval:8.2f}  avg_white_win_rate={avg_wr:.3f}  avg_outcome={avg_out:.3f}")


if __name__ == "__main__":
    main()
