#!/bin/bash
set -euo pipefail

APP_NAME="Clash Verge.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DEST="/Applications/${APP_NAME}"
TMP_MOUNT=""
DMG_PATH=""
RELEASE_URL="https://github.com/clash-verge-rev/clash-verge-rev/releases/download/v2.4.5/Clash.Verge_2.4.5_x64.dmg"
DEFAULT_DMG_PATH="${SCRIPT_DIR}/Clash.Verge_2.4.5_x64.dmg"

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

  if [[ -z "${TMP_MOUNT}" ]]; then
    TMP_MOUNT="$(hdiutil info | awk "${extract_mount}" | tail -n 1 || true)"
  fi

  [[ -n "${TMP_MOUNT}" && -d "${TMP_MOUNT}" ]] || fail "Не удалось смонтировать DMG. Текст hdiutil: ${attach_output}"
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  fail "Этот скрипт только для macOS."
fi

CPU_ARCH="$(uname -m)"
if [[ "${CPU_ARCH}" != "x86_64" ]]; then
  fail "Нужен Intel Mac (x86_64). Текущая архитектура: ${CPU_ARCH}"
fi

OS_VERSION="$(sw_vers -productVersion)"
if [[ "${OS_VERSION}" != 11.* ]]; then
  info "Обнаружена macOS ${OS_VERSION}. Скрипт рассчитан на Big Sur 11.x (может сработать и на более новой версии)."
fi

find_dmg() {
  local exact="${SCRIPT_DIR}/Clash.Verge_2.4.5_x64.dmg"
  if [[ -f "${exact}" ]]; then
    echo "${exact}"
    return
  fi

  local candidate
  candidate="$(find "${SCRIPT_DIR}" -maxdepth 1 -type f -name 'Clash.Verge*_x64*.dmg' | head -n 1 || true)"
  if [[ -n "${candidate}" ]]; then
    echo "${candidate}"
    return
  fi

  candidate="$(find "${SCRIPT_DIR}" -maxdepth 1 -type f -name '*.dmg' | head -n 1 || true)"
  if [[ -n "${candidate}" ]]; then
    echo "${candidate}"
    return
  fi
}

DMG_PATH="$(find_dmg || true)"
if [[ -z "${DMG_PATH}" ]]; then
  info "DMG рядом не найден, скачиваю из GitHub Releases"
  command -v curl >/dev/null 2>&1 || fail "Не найден curl. Установи Command Line Tools или скачай dmg вручную."
  curl -L --fail --output "${DEFAULT_DMG_PATH}" "${RELEASE_URL}" || fail "Не удалось скачать DMG."
  DMG_PATH="${DEFAULT_DMG_PATH}"
fi

info "Очищаю следы прошлых установок (если были)"
sudo launchctl bootout system /Library/LaunchDaemons/io.github.clash-verge-rev.clash-verge-service.plist >/dev/null 2>&1 || true
sudo rm -f /Library/LaunchDaemons/io.github.clash-verge-rev.clash-verge-service.plist >/dev/null 2>&1 || true
sudo rm -rf /Library/Application\ Support/io.github.clash-verge-rev.clash-verge-service >/dev/null 2>&1 || true

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
open "${APP_DEST}"

echo ""
echo "Готово: ${APP_NAME} установлен и запущен."
echo "Если macOS покажет блокировку, открой вручную: Finder -> Applications -> ${APP_NAME} -> Right Click -> Open."
