
# Pawn Chess Agent (TwoFlags) - How to Run

This project contains:
- **Source code** (Python): `client.py`, `ab_agent.py`, `twoflags/` (game logic)
- **Executable** (Windows): `dist/client.exe` (my agent client)
- **Report PDF**: `report-AI.pdf`
- **Optional**: `bonus/` scripts for analyzing tournament logs

---

## Table of Contents
- [Quick start: run a 100-game tournament](#quick-start-run-a-100-game-tournament)
- [Flag explanations](#flag-explanations)
- [How to read the agent output (during a game)](#how-to-read-the-agent-output-during-a-game)
- [Starting from a custom position (Setup)](#starting-from-a-custom-position-setup)
- [Logs: inspect & replay `.moves`](#logs-inspect--replay-moves)
- [Bonus scripts (optional)](#bonus-scripts-optional)

---

## Quick start: run a 100-game tournament

Open **3 terminals** (Windows CMD / PowerShell) and run:

#### 1) Start the tournament server (Terminal 1)

server2p.exe 9999 logs -v --accept-tournament-cmd --elo --elo-baseline 1500 --elo-k 40

#### 2) Run the tournament controller (Terminal 2)
Example: run a 100-game tournament as BLACK using the provided baseline client:

ChessNet.exe --net 127.0.0.1 9999 --side b --tour 100 --random-openings --random-plies 1 --seed 1338

#### 3) Run my agent (Terminal 3)
Play the opposite side (here: WHITE):

dist\client.exe --net 127.0.0.1 9999 --side w -v --seed 1


### Notes

• The client that uses --tour is the tournament controller (it sends the tournament command to the server).

• --random-openings / --random-plies makes the server send different Setup ... starting positions.

• You can swap colors if you want (just keep the two clients on opposite sides).

## Flag explanations
### Common flags (server + clients)
• --net 127.0.0.1 9999
Connect to server at host 127.0.0.1 (localhost) and port 9999.

• --side w / --side b
Force the client to play as White / Black.

• --seed N
Make randomness reproducible (same seed => same random decisions).

•  -v
Verbose protocol printing (recommended for debugging and for screenshots in the report).

## Tournament-only flags (ChessNet tournament controller)
• --tour 100
Run 100 games automatically.

• --random-openings
Use randomized opening setups (server sends Setup ... lines).

• --random-plies 1
Randomize the first 1 ply (half-move).

### ELO flags (server)
• --elo
Enable ELO tracking in server output/logs.

• --elo-baseline 1500
Initial ELO baseline value.

• --elo-k 40
K-factor used by the ELO update formula.

## How to read the agent output (during a game)
Run my agent with -v:

dist\client.exe --net 127.0.0.1 9999 --side w -v --seed 1

You may see messages like:

• Setup ...
The server sends an initial pawn placement. My client loads it and replies OK.

• Time N
Time control message. My client acknowledges with OK.

• Begin
Indicates the side to move first (typically White). If my client is White, it immediately sends its first move.

• Move strings like a2a3 (or a7a8q if promotion is used)
Opponent move received; my client updates its internal board and replies with its chosen move.

## Starting from a custom position (Setup)
What the requirement means
The server may send a line like:

Setup Wb4 Wa3 Wc2 Bg7 Wd4 Bg6 Be7
Each token is 3 chars:

• W / B = pawn color (White / Black)

• file a..h

• rank 1..8

## Logs: inspect & replay .moves
### Inspect .moves
Open it in a text editor, or print it in terminal:

type logs\<timestamp>.moves
Replay .moves
Replay is done using ChessNet (baseline client), not my client.exe:

ChessNet.exe --replay logs\<timestamp>.moves


## Bonus scripts (optional)
This repository includes optional analysis/visualization scripts under bonus/.

Folder structure (example)
Project/                (submission folder)
  bonus/
  out_bonus/            (auto-created by some scripts)
Visualize pawn paths (trajectories)
Run from the Project/ folder:

python bonus\pawn_paths_viz.py "..\Shay Checker v2\logs\tournament_YYYYMMDD_HHMMSS.log"