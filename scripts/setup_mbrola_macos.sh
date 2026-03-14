#!/usr/bin/env bash
set -euo pipefail

echo "[mbrola] build+install to ~/.local (macOS)"

ROOT_TMP="${TMPDIR:-/tmp}/mbrola_build_$$"
mkdir -p "${ROOT_TMP}"
trap 'rm -rf "${ROOT_TMP}"' EXIT

git clone --depth 1 https://github.com/numediart/MBROLA.git "${ROOT_TMP}/MBROLA"
make -C "${ROOT_TMP}/MBROLA" -j"$(sysctl -n hw.ncpu)"

mkdir -p "${HOME}/.local/bin"
cp "${ROOT_TMP}/MBROLA/Bin/mbrola" "${HOME}/.local/bin/mbrola"
chmod +x "${HOME}/.local/bin/mbrola"

mkdir -p "${HOME}/.local/share/mbrola/en1" "${HOME}/.local/share/mbrola/us1" "${HOME}/.local/share/mbrola/us2"
curl -fsSL https://raw.githubusercontent.com/numediart/MBROLA-voices/master/data/en1/en1 -o "${HOME}/.local/share/mbrola/en1/en1"
curl -fsSL https://raw.githubusercontent.com/numediart/MBROLA-voices/master/data/us1/us1 -o "${HOME}/.local/share/mbrola/us1/us1"
curl -fsSL https://raw.githubusercontent.com/numediart/MBROLA-voices/master/data/us2/us2 -o "${HOME}/.local/share/mbrola/us2/us2"

echo "[mbrola] installed:"
ls -lh "${HOME}/.local/bin/mbrola" "${HOME}/.local/share/mbrola/en1/en1" "${HOME}/.local/share/mbrola/us1/us1" "${HOME}/.local/share/mbrola/us2/us2"

cat <<'EOF'

Environment (already applied by run.sh):
  PATH="$HOME/.local/bin:$PATH"
  XDG_DATA_DIRS="$HOME/.local/share:/usr/local/share:/usr/share"

Note:
  On macOS, espeak-ng's MBROLA bridge (mbrowrap) may fail with:
    "/proc is unaccessible"
  The VETKA backend now auto-falls back from mb-* voice to plain espeak voice.
EOF
