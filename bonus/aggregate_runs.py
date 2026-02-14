# bonus/aggregate_runs.py
import argparse
from pathlib import Path
import re

from tlog import parse_tournament_log, compute_elo_from_games

DEPTH_RE = re.compile(r"(?:depth|d)(\d+)", re.IGNORECASE)

def infer_label(path: Path) -> str:
    return path.stem

def infer_clients(games):
    # tries to infer two client names from data
    names = set()
    for g in games:
        names.add(g.white_player)
        names.add(g.black_player)
        if len(names) >= 2:
            break
    names = list(names)
    if len(names) >= 2:
        return names[0], names[1]
    return "CLIENT1", "CLIENT2"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logdir", help="Directory containing multiple tournament logs (ablation runs)")
    ap.add_argument("--glob", default="*.log")
    ap.add_argument("--k", type=float, default=40.0)
    ap.add_argument("--baseline", type=float, default=1500.0)
    args = ap.parse_args()

    logdir = Path(args.logdir)
    paths = sorted(logdir.glob(args.glob))
    if not paths:
        print("No logs found.")
        return

    rows = []
    for p in paths:
        games = parse_tournament_log(str(p))
        if not games:
            continue

        c1, c2 = infer_clients(games)
        r1, r2, w1, w2, n = compute_elo_from_games(games, c1, c2, baseline=args.baseline, k=args.k)

        rows.append({
            "label": infer_label(p),
            "file": p.name,
            "games": n,
            "c1": c1, "c2": c2,
            "c1_wins": int(w1), "c2_wins": int(w2),
            "c1_elo": r1, "c2_elo": r2,
            "c1_delta": r1 - args.baseline,
            "c2_delta": r2 - args.baseline,
        })

    # Print table
    print(f"{'Run':30} | {'Games':>5} | {'C1 wins':>7} | {'C2 wins':>7} | {'C1 ΔELO':>8} | {'C2 ΔELO':>8}")
    print("-" * 90)
    for r in rows:
        print(f"{r['label'][:30]:30} | {r['games']:5d} | {r['c1_wins']:7d} | {r['c2_wins']:7d} | {r['c1_delta']:8.1f} | {r['c2_delta']:8.1f}")

    print("\nTip: Name your logs like:")
    print("  tournament_depth3_full.log")
    print("  tournament_depth3_no_center_control.log")
    print("  tournament_depth3_no_promo_bonus.log")

if __name__ == "__main__":
    main()
