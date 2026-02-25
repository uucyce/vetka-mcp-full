#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$ROOT_DIR/SEREGA_VPN_BUNDLE"
TMP_DIR="$ROOT_DIR/.tmp_goxray"

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR" "$OUT_DIR"

echo "[1/6] Finding latest GoXRay release asset (darwin amd64/x64)..."
API_JSON="$TMP_DIR/release.json"
curl -fsSL "https://api.github.com/repos/goxray/desktop/releases/latest" -o "$API_JSON"

ASSET_URL=$(python3 - <<'PY'
import json
from pathlib import Path
p = Path("tools/vpn_serga/.tmp_goxray/release.json")
data = json.loads(p.read_text(encoding='utf-8'))
assets = data.get('assets', [])
for a in assets:
    name = a.get('name','').lower()
    ok_platform = ('darwin' in name or 'mac' in name) and ('amd64' in name or 'x64' in name)
    ok_ext = name.endswith('.zip') or name.endswith('.dmg') or name.endswith('.tar.xz') or name.endswith('.tar')
    if ok_platform and ok_ext:
        print(a.get('browser_download_url',''))
        break
PY
)

if [[ -z "${ASSET_URL:-}" ]]; then
  echo "[ERROR] Could not find darwin amd64/x64 asset in latest release"
  exit 1
fi

echo "Found: $ASSET_URL"
ASSET_NAME="$(basename "$ASSET_URL")"
ASSET_PATH="$TMP_DIR/$ASSET_NAME"

echo "[2/6] Downloading asset..."
curl -fL "$ASSET_URL" -o "$ASSET_PATH"

EXTRACT_DIR="$TMP_DIR/unpack"
mkdir -p "$EXTRACT_DIR"
APP_PATH=""
BIN_PATH=""

case "$ASSET_NAME" in
  *.zip)
    echo "[3/6] Extracting zip..."
    unzip -q "$ASSET_PATH" -d "$EXTRACT_DIR"
    ;;
  *.dmg)
    echo "[3/6] Extracting dmg..."
    MOUNT_OUT=$(hdiutil attach "$ASSET_PATH" -nobrowse -readonly 2>/dev/null || true)
    VOL=$(echo "$MOUNT_OUT" | awk '/\/Volumes\// {print substr($0, index($0,"/Volumes/")); exit}')
    if [[ -n "${VOL:-}" && -d "$VOL" ]]; then
      cp -R "$VOL"/* "$EXTRACT_DIR/" || true
      hdiutil detach "$VOL" >/dev/null 2>&1 || true
    fi
    ;;
  *.tar.xz)
    echo "[3/6] Extracting tar.xz..."
    tar -xJf "$ASSET_PATH" -C "$EXTRACT_DIR"
    ;;
  *.tar)
    echo "[3/6] Extracting tar..."
    tar -xf "$ASSET_PATH" -C "$EXTRACT_DIR"
    ;;
  *)
    echo "[ERROR] Unsupported asset type: $ASSET_NAME"
    exit 1
    ;;
esac

APP_PATH=$(find "$EXTRACT_DIR" -maxdepth 5 -type d -name "*.app" | head -n 1 || true)
if [[ -z "$APP_PATH" ]]; then
  BIN_PATH=$(find "$EXTRACT_DIR" -maxdepth 5 -type f \( -name "GoXRay" -o -name "goxray" \) | head -n 1 || true)
fi

if [[ -z "$APP_PATH" && -z "$BIN_PATH" ]]; then
  echo "[ERROR] No .app and no GoXRay binary found in archive"
  find "$EXTRACT_DIR" -maxdepth 3 -print
  exit 1
fi

echo "[4/6] Preparing output bundle..."
rm -rf "$OUT_DIR"/*

if [[ -n "$APP_PATH" ]]; then
  cp -R "$APP_PATH" "$OUT_DIR/GoXRay.app"
else
  mkdir -p "$OUT_DIR/GoXRay.app/Contents/MacOS"
  mkdir -p "$OUT_DIR/GoXRay.app/Contents/Resources"
  cp "$BIN_PATH" "$OUT_DIR/GoXRay.app/Contents/MacOS/GoXRay"
  chmod +x "$OUT_DIR/GoXRay.app/Contents/MacOS/GoXRay"
  cat > "$OUT_DIR/GoXRay.app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>GoXRay</string>
  <key>CFBundleDisplayName</key><string>GoXRay</string>
  <key>CFBundleIdentifier</key><string>local.vpn.goxray</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>GoXRay</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict>
</plist>
PLIST
fi

cat > "$OUT_DIR/install.command" <<'SH'
#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/GoXRay.app"

if [ ! -d "$APP" ]; then
  echo "[ERROR] GoXRay.app not found near install.command"
  exit 1
fi

cp -R "$APP" /Applications/
xattr -cr /Applications/GoXRay.app || true
open /Applications/GoXRay.app

echo "[OK] Installed and opened /Applications/GoXRay.app"
SH
chmod +x "$OUT_DIR/install.command"

cat > "$OUT_DIR/test.command" <<'SH'
#!/bin/bash
set -e

echo "[INFO] Testing active SOCKS at 127.0.0.1:12334"
if curl --socks5-hostname 127.0.0.1:12334 https://api.ipify.org --max-time 12; then
  echo
  echo "[OK] SOCKS proxy responds"
else
  echo
  echo "[FAIL] SOCKS proxy does not respond"
  exit 1
fi
SH
chmod +x "$OUT_DIR/test.command"

cat > "$OUT_DIR/README_Сереге.txt" <<'TXT'
1) Двойной клик install.command
2) Откроется GoXRay
3) Вставь subscription URL:
https://proxyliberty.ru/connection/test_proxies_subs/48bb9885-5a2a-4129-9347-3e946e7ca5b9
4) Нажми Connect
5) Если тормозит — переключи сервер (лучше NL/PL/DE)
TXT

echo "[5/6] Clearing quarantine on bundle..."
xattr -cr "$OUT_DIR/GoXRay.app" || true

echo "[6/6] Done"
echo "Bundle ready: $OUT_DIR"
ls -la "$OUT_DIR"
