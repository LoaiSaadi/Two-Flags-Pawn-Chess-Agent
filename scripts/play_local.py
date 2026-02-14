from __future__ import annotations
import argparse
from twoflags.game import Position, apply_move, winner, pretty
from twoflags.notation import parse_move_robust, parse_setup, move_to_str_fr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", type=str, default=None)
    ap.add_argument("--agent", choices=["none", "random", "ab"], default="none")
    ap.add_argument("--agent_side", choices=["W","B","both"], default="B")
    ap.add_argument("--budget", type=float, default=0.15)
    args = ap.parse_args()

    pos = parse_setup(args.setup.split()) if args.setup else Position.initial()
    print(pretty(pos))
    print("Enter moves like e2e4 (or PDF-style 4h2h). Ctrl+C to quit.\n")

    while True:
        w = winner(pos)
        if w is not None:
            print(pretty(pos))
            # print(f"\nGame over. Winner: {w}")
            print(f"\nGame over. Winner: {w} (reason: pawn reached last rank / no pawns / no moves)")
            return

        agent_turn = (args.agent != "none") and (args.agent_side in ("both", pos.turn))
        if agent_turn:
            if args.agent == "random":
                from twoflags.agents.random_agent import choose_move
                mv = choose_move(pos)
            else:
                from twoflags.agents.ab_agent import choose_move_iterdeep
                mv = choose_move_iterdeep(pos, time_budget_sec=args.budget)
            print(f"[agent {pos.turn}] {move_to_str_fr(mv)}")
        else:
            mv = parse_move_robust(input(f"[{pos.turn}] move> ").strip(), pos)

        pos = apply_move(pos, mv)

        # Show updated position
        print(pretty(pos))
        print()

if __name__ == "__main__":
    main()
