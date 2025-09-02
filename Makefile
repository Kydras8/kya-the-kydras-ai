REPO := Kydras8/kya-the-kydras-ai
PY ?= python3
LINT_PATHS := app tray llm scripts

.PHONY: help lint release tag push

help:
\t@echo "Usage:"
\t@echo "  make lint                 # run flake8 (non-fatal)"
\t@echo "  make release v=v0.1.0     # build & publish GitHub release (requires gh)"
\t@echo "  make tag v=v0.1.0         # create & push git tag"
\t@echo "  make push                 # push main"

lint:
\t@ -m pip install -q flake8 || true
\t@flake8  --max-line-length=120 || true

release:
\t@./scripts/release.sh 631763{v:?Missing v. Usage: make release v=vX.Y.Z}

tag:
\t@git tag -a 631763{v:?Missing v. Usage: make tag v=vX.Y.Z} -m "Release 631763{v}"
\t@git push origin 631763{v}

push:
\t@git push -u origin main
