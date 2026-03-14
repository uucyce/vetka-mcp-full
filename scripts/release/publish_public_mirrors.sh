#!/usr/bin/env bash
set -euo pipefail

# Publish modular public mirror repos from monorepo prefixes.
# Source of truth remains monorepo.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAP_FILE="${ROOT_DIR}/scripts/release/public_mirror_map.tsv"

: "${PUBLIC_GH_OWNER:=danilagoleen}"
: "${SOURCE_REF:=HEAD}"
: "${DRY_RUN:=false}"
: "${PUBLIC_MIRROR_VISIBILITY:=public}"  # public|private

TOKEN="${PUBLIC_MIRROR_TOKEN:-${GH_TOKEN:-}}"

if [[ ! -f "${MAP_FILE}" ]]; then
  echo "[mirror] map file not found: ${MAP_FILE}" >&2
  exit 1
fi

if [[ "${DRY_RUN}" != "true" && -z "${TOKEN}" ]]; then
  echo "[mirror] PUBLIC_MIRROR_TOKEN (or GH_TOKEN) is required when DRY_RUN=false" >&2
  exit 1
fi

cd "${ROOT_DIR}"

ensure_repo_exists() {
  local repo_name="$1"
  local http_code

  http_code=$(curl -sS -o /tmp/mirror_repo_check.json -w "%{http_code}" \
    -H "Authorization: token ${TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${PUBLIC_GH_OWNER}/${repo_name}")

  if [[ "${http_code}" == "200" ]]; then
    echo "[mirror] repo exists: ${PUBLIC_GH_OWNER}/${repo_name}"
    return 0
  fi

  if [[ "${http_code}" != "404" ]]; then
    echo "[mirror] cannot check repo ${repo_name}, HTTP ${http_code}" >&2
    cat /tmp/mirror_repo_check.json >&2 || true
    return 1
  fi

  echo "[mirror] creating repo: ${PUBLIC_GH_OWNER}/${repo_name} (${PUBLIC_MIRROR_VISIBILITY})"
  local create_code
  create_code=$(curl -sS -o /tmp/mirror_repo_create.json -w "%{http_code}" \
    -X POST \
    -H "Authorization: token ${TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/user/repos" \
    -d "{\"name\":\"${repo_name}\",\"private\":$([[ \"${PUBLIC_MIRROR_VISIBILITY}\" == \"private\" ]] && echo true || echo false),\"auto_init\":false}")

  if [[ "${create_code}" != "201" ]]; then
    echo "[mirror] failed to create repo ${repo_name}, HTTP ${create_code}" >&2
    cat /tmp/mirror_repo_create.json >&2 || true
    return 1
  fi
}

publish_one() {
  local prefix="$1"
  local repo_name="$2"
  local branch="$3"

  if ! git rev-parse --verify "${SOURCE_REF}" >/dev/null 2>&1; then
    echo "[mirror] source ref not found: ${SOURCE_REF}" >&2
    return 1
  fi

  if ! git ls-tree -d --name-only "${SOURCE_REF}" "${prefix}" | grep -q "^${prefix}$"; then
    echo "[mirror] skip: prefix not found at ${SOURCE_REF}: ${prefix}"
    return 0
  fi

  echo "[mirror] split ${prefix} -> ${repo_name}:${branch}"
  local split_sha
  split_sha="$(git subtree split --prefix="${prefix}" "${SOURCE_REF}")"

  if [[ -z "${split_sha}" ]]; then
    echo "[mirror] split failed for ${prefix}" >&2
    return 1
  fi

  local remote_url="https://x-access-token:${TOKEN}@github.com/${PUBLIC_GH_OWNER}/${repo_name}.git"

  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[mirror][dry-run] would push ${split_sha} -> ${PUBLIC_GH_OWNER}/${repo_name}:${branch}"
    return 0
  fi

  ensure_repo_exists "${repo_name}"
  if ! git push --force "${remote_url}" "${split_sha}:refs/heads/${branch}"; then
    echo "[mirror] push failed for ${repo_name}@${branch}" >&2
    return 1
  fi
  echo "[mirror] published ${repo_name}@${branch}"
}

failures=0
while IFS=$'\t' read -r prefix repo branch; do
  [[ -z "${prefix}" || "${prefix}" =~ ^# ]] && continue
  if ! publish_one "${prefix}" "${repo}" "${branch}"; then
    failures=$((failures + 1))
  fi
done < "${MAP_FILE}"

if [[ ${failures} -gt 0 ]]; then
  echo "[mirror] completed with ${failures} failure(s)" >&2
  exit 1
fi

echo "[mirror] all mirrors published successfully"
