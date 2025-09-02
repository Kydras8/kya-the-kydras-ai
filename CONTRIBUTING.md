# Contributing to Kya — the Kydras AI

## Dev quickstart
1. Install Python 3.11+, pip, and flake8.
2. (Optional) Create a venv and activate it.
3. Run lint locally: `flake8 app tray llm scripts --max-line-length=120`

## Repo layout
- app/: GUI pieces (e.g., `kya_gui.py`)
- tray/: tray notifier (AppIndicator/Notify)
- llm/: LLM helpers (e.g., Qwen/Ollama integration)
- Modelfiles/: Ollama Modelfiles (local aliases)
- profiles/: *.env.example only (no real secrets!)
- scripts/: launchers/wrappers

## Coding style
- Keep functions small and focused; prefer pure functions when possible.
- Use informative docstrings and type hints for new code.
- Keep lines ≤ 120 chars (lint config).

## Commit & PR
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `ci:`
- Branch from `main`; open PRs to `main`.
- Include a short test plan (what you ran, screenshots if UI).

## Security & secrets
- Never commit real `.env` files or API keys.
- Only commit `profiles/*.env.example` with placeholders.

## Screenshots
- Put UI images in `screenshots/` and reference them in the README.
- Keep images lightweight; PNG/JPG under ~1MB each.
