import socket
import time
import random

from twoflags.game import Position, apply_move, winner, generate_moves
from twoflags.notation import parse_setup, parse_move_robust, move_to_str_fr

HOST = "127.0.0.1"
PORT = 5000

# total allowed time for the CLIENT (minutes)
TIME_MINUTES = 0.02  # ~1.2 seconds (change to 1 for real 1 minute)

def recv_some(sock, n=64):
    data = sock.recv(n)
    if not data:
        raise ConnectionError("client disconnected")
    return data

def recv_client_move(sock, timeout_sec):
    """Receive a 4-char move like e2e4. Uses a timeout for realism."""
    sock.settimeout(timeout_sec)
    try:
        data = sock.recv(32)
    except socket.timeout:
        return None
    if not data:
        return None
    # take first 4 non-space chars (works for e2e4)
    s = data.decode("utf-8", errors="ignore").strip()
    s = s.replace(" ", "").replace("-", "").replace("->", "")
    if len(s) < 4:
        return None
    return s[:4]

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"Mock TIME server listening on {HOST}:{PORT}")

    conn, addr = s.accept()
    with conn:
        print("Client connected:", addr)

        # expect initial OK
        got = recv_some(conn, 2)
        print("Got from client:", got)

        setup_line = "Setup Wa2 Wb2 Wc2 Wd2 We2 Wf2 Wg2 Wh2 Ba7 Bb7 Bc7 Bd7 Be7 Bf7 Bg7 Bh7"
        conn.sendall((setup_line + "\n").encode("utf-8"))
        got = recv_some(conn, 2)
        print("Got from client:", got)

        conn.sendall(f"Time {TIME_MINUTES}\n".encode("utf-8"))
        got = recv_some(conn, 2)
        print("Got from client:", got)

        # client plays white
        conn.sendall(b"Begin\n")

        pos = parse_setup(setup_line.split())
        remaining = TIME_MINUTES * 60.0

        while True:
            if winner(pos) is not None:
                print("Game ended. Winner:", winner(pos))
                conn.sendall(b"exit\n")
                break

            # --------- CLIENT TURN (WE COUNT THIS TIME) ----------
            t0 = time.time()
            mv_str = recv_client_move(conn, timeout_sec=max(0.01, remaining))
            t1 = time.time()

            if mv_str is None:
                print("CLIENT TIMEOUT (no move received in time).")
                conn.sendall(b"exit\n")
                break

            spent = t1 - t0
            remaining -= spent
            print(f"Client move: {mv_str}   (spent {spent:.3f}s, remaining {remaining:.3f}s)")

            if remaining < 0:
                print("CLIENT LOST: exceeded total time.")
                conn.sendall(b"exit\n")
                break

            # apply client's move
            mv = parse_move_robust(mv_str, pos)
            pos = apply_move(pos, mv)

            if winner(pos) is not None:
                print("Game ended. Winner:", winner(pos))
                conn.sendall(b"exit\n")
                break

            # --------- SERVER TURN (opponent move) ----------
            moves = list(generate_moves(pos))
            if not moves:
                print("Server has no moves.")
                conn.sendall(b"exit\n")
                break

            smv = random.choice(moves)
            pos = apply_move(pos, smv)
            conn.sendall((move_to_str_fr(smv) + "\n").encode("utf-8"))
