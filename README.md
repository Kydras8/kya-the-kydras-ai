[![Release](https://img.shields.io/github/v/release/Kydras8/kya-the-kydras-ai?display_name=tag)](https://github.com/Kydras8/kya-the-kydras-ai/releases) [![Issues](https://img.shields.io/github/issues/Kydras8/kya-the-kydras-ai)](https://github.com/Kydras8/kya-the-kydras-ai/issues)

[![lint](https://github.com/Kydras8/kya-the-kydras-ai/actions/workflows/lint.yml/badge.svg)](https://github.com/Kydras8/kya-the-kydras-ai/actions/workflows/lint.yml) [![License: MIT](https://img.shields.io/github/license/Kydras8/kya-the-kydras-ai)](LICENSE) ![Stars](https://img.shields.io/github/stars/Kydras8/kya-the-kydras-ai?style=social)

# Kya — the Kydras AI

Helper components and configs for the Kydras System Agent:
- app/kya_gui.py — GUI with "Ask Qwen"
- tray/kya_tray.py — tray notifier (Apply / Dismiss / Open GUI)
- llm/qwen_helper.py — Qwen/Ollama helper (RAG-ready)
- Modelfiles/ — 7B fast alias, 14B ctx-limited alias
- profiles/*.env.example — examples only (no secrets)
- scripts/ — kya, kya-gui, kya-tray, kya-smart, ollama-cap, kya_rag_index.py

## Quick start
1) Build 7B alias:  ollama create qwen7b-coder-ctx4k -f Modelfiles/qwen7b-ctx4k.modelfile
2) (Optional) 14B:  ollama create qwen14b-coder-q4km-ctx4k -f Modelfiles/qwen14b-q4km-ctx4k.modelfile
3) Copy a profile example to ~/.config/kydras/profiles and edit locally.
