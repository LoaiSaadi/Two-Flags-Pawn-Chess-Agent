from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable, List, Set, Literal, Tuple

Color = Literal["W", "B"]
FILES = "abcdefgh"


# =========================
# Square helpers
# =========================
def file_of(sq: int) -> int:
    return sq & 7


def rank_of(sq: int) -> int:
    # 1..8
    return (sq >> 3) + 1


def sq_index(file_idx: int, rank: int) -> int:
    return (rank - 1) * 8 + file_idx


def square_to_fr(sq: Optional[int]) -> Optional[str]:
    if sq is None:
        return None
    return f"{FILES[file_of(sq)]}{rank_of(sq)}"


def fr_to_square(fr: str) -> int:
    """
    'a1'..'h8' -> 0..63
    """
    fr = fr.strip()
    if len(fr) != 2:
        raise ValueError(f"Bad square: {fr!r}")
    f = FILES.find(fr[0])
    if f < 0:
        raise ValueError(f"Bad file: {fr!r}")
    if fr[1] < "1" or fr[1] > "8":
        raise ValueError(f"Bad rank: {fr!r}")
    r = int(fr[1])
    return sq_index(f, r)


# =========================
# Move + Position
# =========================
@dataclass(frozen=True)
class Move:
    src: int
    dst: int
    is_ep: bool = False
    is_double: bool = False


@dataclass
class Position:
    white: Set[int]
    black: Set[int]
    turn: Color = "W"
    ep_target: Optional[int] = None  # passed-over square, valid for one ply

    @staticmethod
    def initial() -> "Position":
        w = {sq_index(f, 2) for f in range(8)}
        b = {sq_index(f, 7) for f in range(8)}
        return Position(white=w, black=b, turn="W", ep_target=None)

    @staticmethod
    def from_setup_tokens(tokens: List[str], turn: Color = "W") -> "Position":
        """
        tokens like: ["Wa2","Wb2",...,"Ba7",...]
        """
        w: Set[int] = set()
        b: Set[int] = set()
        for t in tokens:
            t = t.strip()
            if len(t) < 3:
                continue
            side = t[0]
            sq = fr_to_square(t[1:])
            if side == "W":
                w.add(sq)
            elif side == "B":
                b.add(sq)
            else:
                raise ValueError(f"Bad setup token: {t!r}")
        return Position(white=w, black=b, turn=turn, ep_target=None)

    @staticmethod
    def from_setup_line(line: str, turn: Color = "W") -> "Position":
        """
        line like: "Setup Wa2 Wb2 ... Bh7"
        """
        parts = line.strip().split()
        if not parts or parts[0] != "Setup":
            raise ValueError(f"Not a Setup line: {line!r}")
        return Position.from_setup_tokens(parts[1:], turn=turn)

    def clone(self) -> "Position":
        return Position(set(self.white), set(self.black), self.turn, self.ep_target)

    def occupied(self) -> Set[int]:
        return self.white | self.black


# =========================
# Game rules
# =========================
def winner(pos: Position) -> Optional[Color]:
    # reach last rank
    if any((sq >> 3) == 7 for sq in pos.white):  # rank 8
        return "W"
    if any((sq >> 3) == 0 for sq in pos.black):  # rank 1
        return "B"

    # wipeout
    if not pos.black:
        return "W"
    if not pos.white:
        return "B"

    # no moves = lose
    if not any(True for _ in generate_moves(pos)):
        return "B" if pos.turn == "W" else "W"

    return None


def generate_moves(pos: Position) -> Iterable[Move]:
    """
    Pawn-only:
      - forward 1
      - forward 2 from start rank (creates ep_target)
      - diagonal capture
      - en passant capture to ep_target
    Deterministic order for reproducibility.
    """
    occ = pos.occupied()

    if pos.turn == "W":
        pawns, opp = pos.white, pos.black
        fwd, start_rank = 8, 2
        cap_deltas = (7, 9)      # left then right
        ep_deltas = (7, 9)
    else:
        pawns, opp = pos.black, pos.white
        fwd, start_rank = -8, 7
        cap_deltas = (-9, -7)    # left then right (from Black POV)
        ep_deltas = (-9, -7)

    for src in sorted(pawns):
        r = rank_of(src)
        f = file_of(src)

        # forward 1
        dst1 = src + fwd
        if 0 <= dst1 < 64 and dst1 not in occ:
            yield Move(src, dst1)

            # forward 2 from start
            if r == start_rank:
                dst2 = src + 2 * fwd
                mid = src + fwd
                if 0 <= dst2 < 64 and mid not in occ and dst2 not in occ:
                    yield Move(src, dst2, is_double=True)

        # captures
        for d in cap_deltas:
            dst = src + d
            if 0 <= dst < 64 and abs(file_of(dst) - f) == 1:
                if dst in opp:
                    yield Move(src, dst)

        # en passant
        if pos.ep_target is not None:
            ep = pos.ep_target
            for d in ep_deltas:
                dst = src + d
                if dst == ep and 0 <= dst < 64 and abs(file_of(dst) - f) == 1:
                    cap_sq = dst - fwd  # square of the pawn that moved 2
                    if cap_sq in opp and dst not in occ:
                        yield Move(src, dst, is_ep=True)


def infer_move(pos: Position, src: int, dst: int) -> Move:
    """
    Given a src/dst (from UCI), infer is_double / is_ep from the current position.
    """
    occ = pos.occupied()
    mover = pos.white if pos.turn == "W" else pos.black
    if src not in mover:
        raise ValueError("src is not a pawn of side-to-move")

    fwd = 8 if pos.turn == "W" else -8
    start_rank = 2 if pos.turn == "W" else 7

    is_double = False
    if dst - src == 2 * fwd and rank_of(src) == start_rank:
        # basic path sanity
        mid = src + fwd
        if mid not in occ and dst not in occ:
            is_double = True

    is_ep = False
    if pos.ep_target is not None and dst == pos.ep_target:
        # EP destination is empty; capture pawn behind it
        if dst not in occ and abs(file_of(dst) - file_of(src)) == 1:
            is_ep = True

    return Move(src, dst, is_ep=is_ep, is_double=is_double)


# def apply_move(pos: Position, mv: Move) -> Position:
#     newp = pos.clone()

#     mover = newp.white if newp.turn == "W" else newp.black
#     opp = newp.black if newp.turn == "W" else newp.white
#     fwd = 8 if newp.turn == "W" else -8

#     newp.ep_target = None
#     mover.remove(mv.src)

#     # normal capture
#     if mv.dst in opp:
#         opp.remove(mv.dst)

#     # en passant capture
#     if mv.is_ep:
#         cap_sq = mv.dst - fwd
#         if cap_sq in opp:
#             opp.remove(cap_sq)

#     mover.add(mv.dst)

#     # create ep target after double
#     if mv.is_double:
#         newp.ep_target = mv.src + fwd

#     newp.turn = "B" if newp.turn == "W" else "W"
#     return newp

def apply_move(pos: Position, mv: Move) -> Position:
    newp = pos.clone()

    mover = newp.white if newp.turn == "W" else newp.black
    opp = newp.black if newp.turn == "W" else newp.white
    fwd = 8 if newp.turn == "W" else -8

    # EP target is only valid for one ply
    newp.ep_target = None

    mover.remove(mv.src)

    # normal capture (only if destination is occupied)
    if mv.dst in opp:
        opp.remove(mv.dst)

    # COMPAT MODE (ChessNet):
    # If mv.is_ep, DO NOT remove the "passed" pawn (cap_sq).
    # This keeps our internal state aligned with ChessNet's behavior.

    mover.add(mv.dst)

    # create ep target after double-step
    if mv.is_double:
        newp.ep_target = mv.src + fwd

    newp.turn = "B" if newp.turn == "W" else "W"
    return newp


# =========================
# UCI helpers
# =========================
def uci_to_src_dst(uci: str) -> Tuple[int, int]:
    uci = uci.strip()
    if len(uci) != 4:
        raise ValueError(f"Bad UCI: {uci!r}")
    return fr_to_square(uci[:2]), fr_to_square(uci[2:])


def move_to_uci(mv: Move) -> str:
    return f"{square_to_fr(mv.src)}{square_to_fr(mv.dst)}"


def apply_uci(pos: Position, uci: str) -> Position:
    src, dst = uci_to_src_dst(uci)
    mv = infer_move(pos, src, dst)
    return apply_move(pos, mv)


def pretty(pos: Position) -> str:
    rows: List[str] = []
    for r in range(8, 0, -1):
        row = []
        for f in range(8):
            sq = sq_index(f, r)
            row.append("W" if sq in pos.white else "B" if sq in pos.black else ".")
        rows.append(f"{r} " + " ".join(row))
    rows.append("  " + " ".join(list(FILES)))
    ep = square_to_fr(pos.ep_target) if pos.ep_target is not None else None
    rows.append(f"turn={pos.turn} ep_target={ep}")
    return "\n".join(rows)
