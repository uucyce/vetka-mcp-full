#!/bin/bash
# Verify all mirrors are healthy
# Run: ./scripts/release/verify_mirrors.sh [--fix]

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAP="${ROOT}/scripts/release/public_mirror_map.tsv"

echo "🔍 VETKA Mirror Health Check"
echo "============================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

failures=0
warnings=0

# Check each mirror
while IFS=$'\t' read -r prefix repo branch; do
  [[ -z "$prefix" || "$prefix" =~ ^# ]] && continue
  
  echo ""
  echo "Checking: $repo ($prefix)"
  
  # 1. Check prefix exists
  if git ls-tree "$branch" "$prefix" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅${NC} Prefix exists: $prefix"
  else
    echo -e "  ${RED}❌${NC} Prefix NOT FOUND: $prefix"
    ((failures++))
    continue
  fi
  
  # 2. Test subtree split
  split_sha=$(git subtree split --prefix="$prefix" "$branch" 2>/dev/null)
  if [[ -n "$split_sha" ]]; then
    echo -e "  ${GREEN}✅${NC} Subtree split OK"
  else
    echo -e "  ${RED}❌${NC} Subtree split FAILED"
    ((failures++))
    continue
  fi
  
  # 3. Check last push to GitHub
  last_push=$(gh api "repos/danilagoleen/$repo/commits" --jq '.[0].commit.author.date' 2>/dev/null)
  if [[ -z "$last_push" ]]; then
    echo -e "  ${RED}❌${NC} Cannot fetch last push (repo may not exist)"
    ((failures++))
  else
    # Parse date
    push_date=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$last_push" +%s 2>/dev/null || echo "0")
    now=$(date +%s)
    days=$(( (now - push_date) / 86400 ))
    
    if [[ $days -eq 0 ]]; then
      echo -e "  ${GREEN}✅${NC} Last push: today"
    elif [[ $days -le 3 ]]; then
      echo -e "  ${GREEN}✅${NC} Last push: ${days} day(s) ago"
    elif [[ $days -le 7 ]]; then
      echo -e "  ${YELLOW}⚠️${NC} Last push: ${days} day(s) ago"
      ((warnings++))
    else
      echo -e "  ${RED}❌${NC} Last push: ${days} day(s) ago (STALE)"
      ((failures++))
    fi
  fi
  
  # 4. Check GitHub Actions permissions
  if [[ "${1:-}" == "--fix" ]]; then
    echo "  ℹ️  Run workflow to sync: gh workflow run 'Publish Public Mirrors' -R danilagoleen/vetka"
  fi
  
done < <(grep -v "^#" "$MAP")

echo ""
echo "============================"
if [[ $failures -gt 0 ]]; then
  echo -e "${RED}❌ ${failures} failure(s), ${warnings} warning(s)${NC}"
  exit 1
elif [[ $warnings -gt 0 ]]; then
  echo -e "${YELLOW}⚠️  ${warnings} warning(s), no failures${NC}"
  exit 0
else
  echo -e "${GREEN}✅ All mirrors healthy!${NC}"
  exit 0
fi
