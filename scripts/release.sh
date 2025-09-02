#!/usr/bin/env bash
set -euo pipefail
REPO="Kydras8/kya-the-kydras-ai"
VER="${1:-}"
[ -n "$VER" ] || { echo "Usage: $0 vX.Y.Z"; exit 1; }
command -v gh >/dev/null || { echo "gh CLI required"; exit 1; }
gh auth status >/dev/null || { echo "gh not authenticated"; exit 1; }

# build artifacts
DIST="dist/$VER"
rm -rf "$DIST"; mkdir -p "$DIST"
# include safe artifacts only
[ -d Modelfiles ] && cp -a Modelfiles "$DIST/"
mkdir -p "$DIST/profiles"
cp profiles/*.env.example "$DIST/profiles/" 2>/dev/null || true
cp README.md LICENSE  "$DIST/" 2>/dev/null || true

# archives + checksums
( cd dist && printf "%s\n" "$VER" > VERSION.txt )
( cd dist && zip -r "kya-$VER.zip" "$VER" >/dev/null )
( cd dist && tar -czf "kya-$VER.tgz" "$VER" )
( cd dist && sha256sum "kya-$VER.zip" "kya-$VER.tgz" > "kya-$VER.sha256" )

# tag + push
git tag -a "$VER" -m "Release $VER" || true
git push origin "$VER"

# create (or update) release
gh release view "$VER" -R "$REPO" >/dev/null 2>&1 ||   gh release create "$VER" -R "$REPO" -t "Kya $VER" -n "Artifacts and examples for $VER"

# upload assets
gh release upload "$VER" dist/"kya-$VER.zip" dist/"kya-$VER.tgz" dist/"kya-$VER.sha256" -R "$REPO" --clobber
echo "[ok] Release $VER published."
