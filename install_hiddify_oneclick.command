#!/bin/bash
set -euo pipefail

APP_NAME="Hiddify.app"
APP_DEST="/Applications/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_URL="https://api.github.com/repos/hiddify/hiddify-app/releases/latest"
FALLBACK_URL="https://github.com/hiddify/hiddify-app/releases/latest/download/Hiddify-MacOS.dmg"
DMG_PATH=""
TMP_MOUNT=""

cleanup() {
  if [[ -n "${TMP_MOUNT}" && -d "${TMP_MOUNT}" ]]; then
    hdiutil detach "${TMP_MOUNT}" -quiet >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

fail() {
  echo ""
  echo "[ERROR] $1"
  echo ""
  exit 1
}

info() {
  echo "[INFO] $1"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Не найдено: $1"
}

mount_dmg() {
  local dmg="$1"
  local attach_output=""
  local extract_mount='
    /\/Volumes\// {
      pos = index($0, "/Volumes/");
      if (pos > 0) print substr($0, pos);
    }
  '

  attach_output="$(hdiutil attach "${dmg}" -nobrowse 2>&1 || true)"
  TMP_MOUNT="$(echo "${attach_output}" | awk "${extract_mount}" | tail -n 1)"
  [[ -n "${TMP_MOUNT}" && -d "${TMP_MOUNT}" ]] || fail "Не удалось смонтировать DMG. ${attach_output}"
}

select_latest_dmg_url() {
  local json="$1"
  local line=""

  line="$(echo "${json}" | grep -Eo '"browser_download_url":[[:space:]]*"[^"]+\.dmg"' \
    | grep -Ei 'mac|darwin' \
    | head -n 1 || true)"

  if [[ -z "${line}" ]]; then
    line="$(echo "${json}" | grep -Eo '"browser_download_url":[[:space:]]*"[^"]+\.dmg"' | head -n 1 || true)"
  fi

  if [[ -n "${line}" ]]; then
    echo "${line}" | sed -E 's/.*"([^"]+)"/\1/'
  fi
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  fail "Этот скрипт только для macOS."
fi

need_cmd curl
need_cmd hdiutil
need_cmd ditto

CPU_ARCH="$(uname -m)"
OS_VERSION="$(sw_vers -productVersion || true)"
info "macOS ${OS_VERSION}, CPU ${CPU_ARCH}"

RELEASE_JSON="$(curl -L --fail --silent "${API_URL}" || true)"
DMG_URL="$(select_latest_dmg_url "${RELEASE_JSON}" || true)"
if [[ -z "${DMG_URL}" ]]; then
  DMG_URL="${FALLBACK_URL}"
fi

DMG_PATH="${SCRIPT_DIR}/Hiddify-MacOS-latest.dmg"
if [[ -f "${DMG_PATH}" ]]; then
  info "Использую локальный DMG: ${DMG_PATH}"
else
  info "Локальный DMG не найден, скачиваю Hiddify Next"
  curl -L --fail --output "${DMG_PATH}" "${DMG_URL}" || fail "Не удалось скачать DMG: ${DMG_URL}"
fi

info "Монтирую $(basename "${DMG_PATH}")"
mount_dmg "${DMG_PATH}"

APP_SOURCE="${TMP_MOUNT}/${APP_NAME}"
[[ -d "${APP_SOURCE}" ]] || fail "В DMG не найден ${APP_NAME}."

info "Устанавливаю ${APP_NAME} в /Applications"
if [[ -d "${APP_DEST}" ]]; then
  sudo rm -rf "${APP_DEST}"
fi
sudo ditto "${APP_SOURCE}" "${APP_DEST}"

info "Снимаю quarantine и запускаю"
sudo xattr -rd com.apple.quarantine "${APP_DEST}" >/dev/null 2>&1 || true
open "${APP_DEST}" || fail "Не удалось запустить ${APP_NAME}"

echo ""
echo "Готово: ${APP_NAME} установлен и запущен."
