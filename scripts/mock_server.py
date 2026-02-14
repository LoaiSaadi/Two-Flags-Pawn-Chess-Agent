import socket
import time

HOST = "127.0.0.1"
PORT = 5000

def recv_line(conn) -> str:
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = conn.recv(1)
        if not chunk:
            raise ConnectionError("client disconnected")
        buf += chunk
    return buf.decode("utf-8", errors="replace").strip()

def send_line(conn, s: str):
    conn.sendall((s + "\n").encode("utf-8"))

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"Mock server listening on {HOST}:{PORT}")

    conn, addr = s.accept()
    with conn:
        print("Client connected:", addr)

        # 1) Client should send OK immediately
        got = recv_line(conn)
        print("Got from client:", got)

        # 2) Send custom Setup -> expect OK
        setup = "Setup Wb4 Wa3 Wc2 Bg7 Wd4 Bg6 Be7"
        print("Sending:", setup)
        send_line(conn, setup)

        got = recv_line(conn)
        print("Got from client:", got)  # should be OK

        # 3) Send Time -> expect OK
        send_line(conn, "Time 1")
        got = recv_line(conn)
        print("Got from client:", got)  # should be OK

        # 4) Begin -> client must play first (White)
        send_line(conn, "Begin")

        # 5) Read client move (White)
        mv = recv_line(conn)
        print("Client move:", mv)

        # 6) Send a LEGAL black move from this setup (e7e6)
        time.sleep(0.2)
        black_mv = "e7e6"
        print("Sending black move:", black_mv)
        send_line(conn, black_mv)

        # 7) Read client reply
        mv2 = recv_line(conn)
        print("Client reply:", mv2)

        # 8) Finish
        send_line(conn, "exit")
        print("Sent exit, closing.")
