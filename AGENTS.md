# AGENTS.md

## Project overview

**Tank Battle 2D** (`Projekt_SI`) is a single-process Python/Pygame desktop game. Entry point: `main.py` from the repository root (so `Maps/` and `Maps2/` resolve correctly).

## Cursor Cloud specific instructions

### Services

| Service | Required | Notes |
|---------|----------|--------|
| Tank Battle 2D (`python3 main.py`) | Yes | Only runtime component; no DB, Docker, or network services |

### Dependencies

- Python 3.12+ (3.13 works per `.idea` config)
- `pygame` — install via `pip3 install --user -r requirements.txt` (see VM update script)
- **Display**: Cloud Agent VMs expose `DISPLAY=:1` for GUI testing. On headless shells without a desktop, use `xvfb-run -a python3 main.py`.

### Run (development)

```bash
cd /workspace   # repo root
python3 main.py
```

Headless smoke test:

```bash
timeout 3 xvfb-run -a python3 main.py
```

Expect harmless **ALSA** warnings when no audio device is present.

### Controls (for manual / computer-use testing)

- **Menu**: Up/Down to select mode, Enter to confirm
- **Deathmatch settings**: Left/Right for enemy count (1–3), Enter to start, Esc back
- **Gameplay**: WASD or arrows to move, Space to shoot, R to return to menu after game over

### Lint / tests

No project linter or automated test suite is configured. Basic validation:

```bash
python3 -m py_compile *.py
python3 -c "import pygame; from main import get_random_map; print(get_random_map())"
```

### Long-running processes

Use **tmux** for the game window (it blocks the terminal). Example session name: `tank-battle-game`.
