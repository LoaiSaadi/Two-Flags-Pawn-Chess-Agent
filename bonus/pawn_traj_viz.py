# bonus/pawn_traj_viz.py
import argparse
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt

from tlog import parse_tournament_log, PawnBoard, sq_to_xy

def draw_board(ax):
    ax.set_xlim(-0.5, 7.5)
    ax.set_ylim(-0.5, 7.5)
    ax.set_xticks(range(8))
    ax.set_yticks(range(8))
    ax.set_xticklabels(list("abcdefgh"))
    ax.set_yticklabels([str(i) for i in range(1, 9)])
    ax.grid(True)
    ax.set_aspect("equal")

def save_heatmap(counts, out_png: Path, title: str):
    fig, ax = plt.subplots(figsize=(6, 6))
    draw_board(ax)
    # imshow expects [y][x]
    mat = [[counts[(x, y)] for x in range(8)] for y in range(8)]
    ax.imshow(mat, origin="lower", extent=(-0.5, 7.5, -0.5, 7.5), alpha=0.85)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)

def save_game_trajectories(game, out_png: Path):
    board = PawnBoard()
    for mv in game.moves:
        board.apply(mv)

    fig, ax = plt.subplots(figsize=(6, 6))
    draw_board(ax)
    ax.set_title(f"Game {game.gid}: {game.white_player}(W) vs {game.black_player}(B) | winner={game.winner_side}")

    # Plot each pawn path as a polyline
    for pid, path in board.paths.items():
        if len(path) < 2:
            continue
        pts = [sq_to_xy(sq) for sq in path]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, marker="o", linewidth=1, alpha=0.8)

    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile")
    ap.add_argument("--outdir", default="out_bonus")
    ap.add_argument("--game", type=int, nargs="*", help="Render specific game IDs (e.g., --game 96 97)")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    games = parse_tournament_log(args.logfile)

    # Aggregate heatmaps: count visits by square for WHITE/BLACK pawns
    counts_w = defaultdict(int)
    counts_b = defaultdict(int)

    for g in games:
        board = PawnBoard()
        for mv in g.moves:
            board.apply(mv)
        for pid, path in board.paths.items():
            for sq in path:
                x, y = sq_to_xy(sq)
                if pid.startswith("W_"):
                    counts_w[(x, y)] += 1
                else:
                    counts_b[(x, y)] += 1

    save_heatmap(counts_w, outdir / "heatmap_white.png", "WHITE pawn square-visit heatmap (all games)")
    save_heatmap(counts_b, outdir / "heatmap_black.png", "BLACK pawn square-visit heatmap (all games)")

    # Optional per-game trajectories
    if args.game:
        by_id = {g.gid: g for g in games}
        for gid in args.game:
            if gid in by_id:
                save_game_trajectories(by_id[gid], outdir / f"traj_game_{gid}.png")

    print(f"Saved: {outdir / 'heatmap_white.png'}")
    print(f"Saved: {outdir / 'heatmap_black.png'}")
    if args.game:
        print(f"Saved game trajectory images in: {outdir}")

if __name__ == "__main__":
    main()
