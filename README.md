# Pawn Chess Agent (TwoFlags) — How to Run

This project contains:
- **Source code** (Python): `client.py`, `ab_agent.py`, `twoflags/` (game logic)
- **Executable** (Windows): `dist/client.exe` (my agent client)
- **Report PDF**: `report-AI.pdf`
- **Optional**: `bonus/` scripts for analyzing tournament logs

---

## Table of Contents
- [Quick start: play one game](#quick-start-play-one-game)
- [Run a 100-game tournament (Part C)](#run-a-100-game-tournament-part-c)
- [Flag explanations](#flag-explanations)
- [How to read the agent output (during a game)](#how-to-read-the-agent-output-during-a-game)
- [Starting from a custom position (Setup)](#starting-from-a-custom-position-setup)
- [Logs: inspect & replay `.moves`](#logs-inspect--replay-moves)
- [Rebuilding `dist/client.exe` (optional)](#rebuilding-distclientexe-optional)
- [Bonus scripts (optional)](#bonus-scripts-optional)

---

## Quick start: play one game

Open **3 terminals** (Windows CMD/PowerShell) and run:


1) Start the tournament server (Terminal 1)
server2p.exe 9999 logs -v --accept-tournament-cmd --elo --elo-baseline 1500 --elo-k 40

2) Run the tournament controller (Terminal 2)
Example: run a 100-game tournament as BLACK using the provided baseline client:

ChessNet.exe --net 127.0.0.1 9999 --side b --tour 100 --random-openings --random-plies 1 --seed 1338

3) Run my agent (Terminal 3)
Play the opposite side (here: WHITE):

dist\client.exe --net 127.0.0.1 9999 --side w -v --seed 1
Notes

The client that uses --tour is the one that sends the tournament command to the server.

--random-openings / --random-plies makes the server send different Setup ... positions at the start of games.

You can swap colors if you want (just keep the two clients on opposite sides).


----------------------------------------------


### Flag explanations:
--net 127.0.0.1 9999 — connect to server at host 127.0.0.1 (localhost) and port 9999

--side w / --side b — play as White / Black

--tour 100 — run 100 games automatically (tournament controller)

--random-openings — use randomized opening setups (server sends Setup ...)

--random-plies 1 — randomize the first 1 ply (half-move)

--seed 1338 / --seed 1 — make randomness reproducible

-v — verbose mode (prints protocol lines like [client] <- Setup ...)


-------------------------------------------------


### How to read the agent output (during a game)

When you run my client with -v, you may see messages like:

- Setup ... — the server sends an initial position (custom pawn placement).
My client loads it and replies OK.

- Time N — time control (my client acknowledges with OK).

- Begin — indicates my client should play first as White.

- Move strings like a2a3 — opponent move; my client updates its internal board and replies with its move.




---------------------------
### Bonus scripts (optional)

This repository includes optional analysis/visualization scripts under bonus/.

Folder structure (example)
Project/ ✅ (submission folder)
    bonus/
    out_bonus/ (auto-created by some scripts)

---------------------------


### Visualize pawn paths (trajectories)
Run from the Project/ folder:

python bonus\pawn_paths_viz.py "..tournament_YYYYMMDD_HHMMSS.log"