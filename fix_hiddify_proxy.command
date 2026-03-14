#!/bin/bash
set -euo pipefail

SOCKS_HOST="127.0.0.1"
SOCKS_PORT="12334"
MODE="${1:-on}"

fail() {
  echo ""
  echo "[ERROR] $1"
  echo ""
  echo "Использование:"
  echo "  ./fix_hiddify_proxy.command on"
  echo "  ./fix_hiddify_proxy.command off"
  exit 1
}

info() {
  echo "[INFO] $1"
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  fail "Скрипт только для macOS."
fi

if [[ "${MODE}" != "on" && "${MODE}" != "off" ]]; then
  fail "Параметр должен быть: on или off."
fi

command -v networksetup >/dev/null 2>&1 || fail "Не найден networksetup."

ACTIVE_IF="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')"
[[ -n "${ACTIVE_IF}" ]] || fail "Не найден активный сетевой интерфейс."

ACTIVE_SERVICE="$(
  networksetup -listnetworkserviceorder \
  | awk -v iface="${ACTIVE_IF}" '
      /Hardware Port:/ {
        svc = $0
        sub(/^.*Hardware Port: /, "", svc)
        sub(/, Device: .*$/, "", svc)
      }
      $0 ~ "Device: " iface "\\)" {
        print svc
        exit
      }
    '
)"

if [[ -z "${ACTIVE_SERVICE}" ]]; then
  # fallback: first enabled service
  ACTIVE_SERVICE="$(networksetup -listallnetworkservices | awk 'NR>1 && $0 !~ /^\*/ {print; exit}')"
fi

[[ -n "${ACTIVE_SERVICE}" ]] || fail "Не удалось определить сетевой сервис."

info "Активный интерфейс: ${ACTIVE_IF}"
info "Сетевой сервис: ${ACTIVE_SERVICE}"

if [[ "${MODE}" == "on" ]]; then
  info "Включаю SOCKS proxy ${SOCKS_HOST}:${SOCKS_PORT}"
  sudo networksetup -setsocksfirewallproxy "${ACTIVE_SERVICE}" "${SOCKS_HOST}" "${SOCKS_PORT}"
  sudo networksetup -setsocksfirewallproxystate "${ACTIVE_SERVICE}" on
else
  info "Выключаю SOCKS proxy"
  sudo networksetup -setsocksfirewallproxystate "${ACTIVE_SERVICE}" off
fi

echo ""
echo "Текущий статус SOCKS:"
networksetup -getsocksfirewallproxy "${ACTIVE_SERVICE}" || true
