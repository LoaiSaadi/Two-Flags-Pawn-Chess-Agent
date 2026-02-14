import argparse
import random
import socket
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

FILES = "abcdefgh"
RANKS = "12345678"
PROMO_CHARS = set("qQrRbBnN")  # allow common promotion suffixes


def sq_to_xy(sq: str) -> Tuple[int, int]:
    f = FILES.index(sq[0])
    r = RANKS.index(sq[1])
    return f, r


def xy_to_sq(x: int, y: int) -> str:
    return f"{FILES[x]}{RANKS[y]}"


def is_move(s: str) -> bool:
    # Accept: a2a3 OR a7a8q
    if len(s) == 4:
        core = s
        promo = None
    elif len(s) == 5:
        core = s[:4]
        promo = s[4]
        if promo not in PROMO_CHARS:
            return False
    else:
        return False

    return (
        len(core) == 4
        and core[0] in FILES and core[2] in FILES
        and core[1] in RANKS and core[3] in RANKS
    )


def move_core(s: str) -> str:
    # Strip promotion suffix if present
    return s[:4]


@dataclass(frozen=True)
class Move:
    fx: int
    fy: int
    tx: int
    ty: int

    def to_str(self) -> str:
        return xy_to_sq(self.fx, self.fy) + xy_to_sq(self.tx, self.ty)


class PawnBoard:
    """
    Pawn-only chess board.

    DEFAULT RULES (standard pawns):
      - forward 1 to empty
      - forward 2 from start rank if both empty
      - diagonal 1 ONLY if capturing opponent

    Optional variant:
      --diag-empty  => diagonal 1 also allowed into empty (non-standard)
    """
    def __init__(self, diag_empty: bool = False) -> None:
        self.diag_empty = diag_empty
        self.grid: List[List[Optional[str]]] = [[None for _ in range(8)] for _ in range(8)]
        self.reset_to_start()

    def clear(self) -> None:
        for y in range(8):
            for x in range(8):
                self.grid[y][x] = None

    def reset_to_start(self) -> None:
        self.clear()
        for x in range(8):
            self.grid[1][x] = "W"
            self.grid[6][x] = "B"

    def load_from_setup(self, tokens: List[str]) -> None:
        self.clear()
        for t in tokens:
            if len(t) != 3:
                continue
            c = t[0]
            sq = t[1:]
            if c not in ("W", "B"):
                continue
            x, y = sq_to_xy(sq)
            self.grid[y][x] = c

    def piece_at(self, x: int, y: int) -> Optional[str]:
        return self.grid[y][x]

    def set_piece(self, x: int, y: int, p: Optional[str]) -> None:
        self.grid[y][x] = p

    def legal_moves(self, side: str) -> List[Move]:
        opp = "B" if side == "W" else "W"
        diry = 1 if side == "W" else -1
        start_rank = 1 if side == "W" else 6

        moves: List[Move] = []
        for y in range(8):
            for x in range(8):
                if self.grid[y][x] != side:
                    continue

                ny = y + diry
                if not (0 <= ny < 8):
                    continue

                # forward 1
                if self.grid[ny][x] is None:
                    moves.append(Move(x, y, x, ny))

                    # forward 2
                    if y == start_rank:
                        ny2 = y + 2 * diry
                        if 0 <= ny2 < 8 and self.grid[ny2][x] is None:
                            moves.append(Move(x, y, x, ny2))

                # diagonal 1
                for dx in (-1, 1):
                    nx = x + dx
                    if not (0 <= nx < 8):
                        continue
                    target = self.grid[ny][nx]
                    if target == opp:
                        moves.append(Move(x, y, nx, ny))
                    elif self.diag_empty and target is None:
                        moves.append(Move(x, y, nx, ny))

        return moves

    def apply_move(self, mv: Move, side: str) -> bool:
        fx, fy, tx, ty = mv.fx, mv.fy, mv.tx, mv.ty
        piece = self.piece_at(fx, fy)
        if piece != side:
            return False

        opp = "B" if side == "W" else "W"
        diry = 1 if side == "W" else -1
        start_rank = 1 if side == "W" else 6

        dx = tx - fx
        dy = ty - fy

        # forward
        if dx == 0:
            if dy not in (diry, 2 * diry):
                return False
            if self.piece_at(tx, ty) is not None:
                return False
            if dy == 2 * diry:
                if fy != start_rank:
                    return False
                midy = fy + diry
                if self.piece_at(tx, midy) is not None:
                    return False

        # diagonal
        elif abs(dx) == 1 and dy == diry:
            target = self.piece_at(tx, ty)
            if target == side:
                return False
            if target is None and not self.diag_empty:
                return False
            if target is not None and target != opp:
                return False
        else:
            return False

        self.set_piece(fx, fy, None)
        self.set_piece(tx, ty, side)
        return True

    def apply_move_str(self, s: str, side: str) -> bool:
        s = move_core(s)
        fx, fy = sq_to_xy(s[:2])
        tx, ty = sq_to_xy(s[2:])
        return self.apply_move(Move(fx, fy, tx, ty), side)

    def force_apply_move_str(self, s: str, side: str) -> None:
        s = move_core(s)
        fx, fy = sq_to_xy(s[:2])
        tx, ty = sq_to_xy(s[2:])
        self.set_piece(fx, fy, None)
        self.set_piece(tx, ty, side)


def pick_move(board: PawnBoard, side: str, rng: random.Random) -> Optional[Move]:
    moves = board.legal_moves(side)
    if not moves:
        return None

    goal_rank = 7 if side == "W" else 0
    winners = [m for m in moves if m.ty == goal_rank]
    if winners:
        return rng.choice(winners)

    opp = "B" if side == "W" else "W"
    caps = [m for m in moves if board.piece_at(m.tx, m.ty) == opp]
    if caps:
        return rng.choice(caps)

    def score(m: Move) -> int:
        return m.ty if side == "W" else (7 - m.ty)

    moves.sort(key=score, reverse=True)
    top = moves[: min(12, len(moves))]
    return rng.choice(top)


class NetIO:
    def __init__(self, host: str, port: int, verbose: bool) -> None:
        self.verbose = verbose
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.f = self.sock.makefile("rwb", buffering=0)

    def send_line(self, s: str) -> None:
        if self.verbose:
            print(f"[client] -> {s}")
        self.f.write((s + "\n").encode("utf-8"))

    def recv_line(self) -> Optional[str]:
        line = self.f.readline()
        if not line:
            return None
        s = line.decode("utf-8", errors="replace").strip()
        if self.verbose:
            print(f"[client] <- {s}")
        return s

    def close(self) -> None:
        try:
            self.f.close()
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


def parse_time_to_seconds(n: int, unit: str) -> float:
    # unit: auto|sec|min
    if unit == "sec":
        return float(n)
    if unit == "min":
        return float(n) * 60.0
    # auto: common tournaments give minutes (small numbers), seconds give bigger numbers (e.g., 300)
    if n <= 30:
        return float(n) * 60.0
    return float(n)


def maybe_add_promo(move_str4: str, side: str, use_promo: bool, promo_char: str) -> str:
    if not use_promo:
        return move_str4
    # if move ends on last rank => append promo char
    dst = move_str4[2:]
    if (side == "W" and dst[1] == "8") or (side == "B" and dst[1] == "1"):
        return move_str4 + promo_char
    return move_str4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", nargs=2, metavar=("HOST", "PORT"), required=True)
    ap.add_argument("--side", choices=["w", "b", "auto"], default="auto",
                    help="If set, we EXPECT to be that side. 'auto' infers: Begin=>White else Black.")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--diag-empty", action="store_true")
    ap.add_argument("--time-unit", choices=["auto", "sec", "min"], default="auto",
                    help="Server 'Time N' unit. auto assumes minutes if N<=30 else seconds.")
    ap.add_argument("--promo", choices=["auto", "off", "q", "Q"], default="auto",
                    help="Promotion suffix policy. auto=enable only if server ever sends 5-char moves.")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    host, port_s = args.net
    port = int(port_s)
    rng = random.Random(args.seed)

    io = NetIO(host, port, args.verbose)
    print("Connected.")

    board = PawnBoard(diag_empty=args.diag_empty)

    my_side: Optional[str] = None
    time_left_sec: Optional[float] = None

    # Promotion policy
    server_uses_promo = False
    promo_forced_off = (args.promo == "off")
    promo_forced_on = (args.promo in ("q", "Q"))
    promo_char = args.promo if promo_forced_on else "q"

    io.send_line("OK")

    while True:
        msg = io.recv_line()
        if msg is None:
            print("Server disconnected.")
            break

        if msg.startswith("TournamentAccepted"):
            continue

        if msg == "Reset":
            io.send_line("Ready")
            my_side = None
            board.reset_to_start()
            time_left_sec = None
            continue

        if msg.startswith("Setup "):
            board.load_from_setup(msg.split()[1:])
            io.send_line("OK")
            continue

        if msg.startswith("Time "):
            try:
                n = int(msg.split()[1])
                time_left_sec = parse_time_to_seconds(n, args.time_unit)
            except Exception:
                time_left_sec = None
            io.send_line("OK")
            continue

        if msg == "Begin":
            my_side = "W"
            t0 = time.perf_counter()

            mv_obj = pick_move(board, my_side, rng)
            if mv_obj is None:
                io.send_line("exit")
            else:
                mv4 = mv_obj.to_str()
                use_promo = (not promo_forced_off) and (promo_forced_on or server_uses_promo)
                out = maybe_add_promo(mv4, my_side, use_promo, promo_char)

                board.apply_move_str(out, my_side)
                io.send_line(out)

            if time_left_sec is not None:
                time_left_sec -= (time.perf_counter() - t0)
            continue

        if msg == "exit":
            continue

        if msg.startswith("GameOver"):
            my_side = None
            continue

        # Moves (4 or 5 chars)
        if is_move(msg):
            if len(msg) == 5:
                server_uses_promo = True

            if my_side is None:
                my_side = "B"

            opp = "B" if my_side == "W" else "W"

            ok = board.apply_move_str(msg, opp)
            if not ok:
                if args.verbose:
                    print(f"[client] WARN: rejected opponent move {msg} for {opp}; forcing apply to stay synced.")
                board.force_apply_move_str(msg, opp)

            # Our reply
            t0 = time.perf_counter()

            mv_obj = pick_move(board, my_side, rng)
            if mv_obj is None:
                io.send_line("exit")
                continue

            use_promo = (not promo_forced_off) and (promo_forced_on or server_uses_promo)

            sent = False
            for _ in range(10):
                mv4 = mv_obj.to_str()
                out = maybe_add_promo(mv4, my_side, use_promo, promo_char)

                if board.apply_move_str(out, my_side):
                    io.send_line(out)
                    sent = True
                    break

                legals = board.legal_moves(my_side)
                if not legals:
                    io.send_line("exit")
                    sent = True
                    break
                mv_obj = rng.choice(legals)

            if not sent:
                io.send_line("exit")

            if time_left_sec is not None:
                time_left_sec -= (time.perf_counter() - t0)
            continue

        # Unknown messages: in verbose, print them (helps detect "IllegalMove"/timeouts)
        if args.verbose:
            print(f"[client] INFO: unhandled server msg: {msg}")

    io.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
