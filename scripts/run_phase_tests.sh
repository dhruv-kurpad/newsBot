#!/usr/bin/env bash
# Run NewsBot phase tests individually or all at once.
#
# Usage:
#   ./scripts/run_phase_tests.sh           # all phases
#   ./scripts/run_phase_tests.sh 0         # phase 0 only
#   ./scripts/run_phase_tests.sh 3 4       # phases 3 and 4
#   ./scripts/run_phase_tests.sh all       # all phases

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ $# -eq 0 || "${1:-}" == "all" ]]; then
  echo "Running all phase tests…"
  exec python -m pytest tests/ "$@"
fi

markers=()
args=()
for arg in "$@"; do
  if [[ "$arg" =~ ^[0-7]$ ]]; then
    markers+=("phase${arg}")
  else
    args+=("$arg")
  fi
done

if [[ ${#markers[@]} -eq 0 ]]; then
  exec python -m pytest tests/ "${args[@]}"
fi

expr="$(IFS=' or '; echo "${markers[*]}")"
echo "Running markers: ${expr}"
exec python -m pytest -m "${expr}" "${args[@]}"
