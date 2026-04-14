#!/bin/zsh
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/run_benchmark_validation.sh SPEC_PATH [profiles_csv] [--fast]"
  exit 1
fi

SPEC_PATH="$1"
PROFILES="${2:-base,frontier_ai,enterprise_ai,physical_ai}"
EXTRA_ARGS=("${@:3}")
DB_PATH="/tmp/brand3-benchmark-$(date +%Y%m%d-%H%M%S).sqlite3"

echo "Using temp DB: ${DB_PATH}"
echo "Spec: ${SPEC_PATH}"
echo "Profiles: ${PROFILES}"
if (( ${#EXTRA_ARGS[@]} > 0 )); then
  echo "Extra args: ${EXTRA_ARGS[*]}"
fi

env \
  BRAND3_DB_PATH="${DB_PATH}" \
  BRAND3_CACHE_TTL_HOURS=0 \
  /Users/gsus/brand3-scoring/.venv/bin/python \
  /Users/gsus/brand3-scoring/main.py \
  benchmark \
  --spec "${SPEC_PATH}" \
  --profiles "${PROFILES}" \
  "${EXTRA_ARGS[@]}"
