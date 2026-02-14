# bonus/opening_stats.py
import argparse
from collections import defaultdict

from tlog import parse_tournament_log

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile")
    ap.add_argument("--plies", type=int, default=6, help="Opening length in plies (default 6 = 3 full moves)")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    games = parse_tournament_log(args.logfile)

    stats = defaultdict(lambda: {"count": 0, "white_wins": 0, "black_wins": 0})

    for g in games:
        seq = []
        for mv in g.moves[:args.plies]:
            seq.append(f"{mv.frm}{mv.to}")
        key = " ".join(seq) if seq else "(empty)"
        stats[key]["count"] += 1
        if g.winner_side == "WHITE":
            stats[key]["white_wins"] += 1
        elif g.winner_side == "BLACK":
            stats[key]["black_wins"] += 1

    # Sort by frequency
    items = sorted(stats.items(), key=lambda kv: kv[1]["count"], reverse=True)[:args.top]

    print(f"Top {args.top} openings by first {args.plies} plies\n")
    print(f"{'Count':>5} | {'W%':>6} | {'B%':>6} | Opening sequence")
    print("-" * 80)
    for key, v in items:
        c = v["count"]
        w = v["white_wins"]
        b = v["black_wins"]
        w_pct = 100.0 * w / c if c else 0.0
        b_pct = 100.0 * b / c if c else 0.0
        print(f"{c:5d} | {w_pct:5.1f}% | {b_pct:5.1f}% | {key}")

if __name__ == "__main__":
    main()
