#!/usr/bin/env bash
set -euo pipefail

mkdir -p "${EVE_EVAL_LOG_ROOT:?}"
score_path="$EVE_EVAL_LOG_ROOT/score.yaml"

write_fallback_score() {
  if [[ ! -f "$score_path" ]]; then
    cat >"$score_path" <<'EOF'
score: 0.0
summary: primary discovery evaluation failed before scoring
status: failed
discovery_ready: false
EOF
  fi
}
trap write_fallback_score EXIT

"${LLMAO_PHASE12_ADAPTER_PYTHON:?set LLMAO_PHASE12_ADAPTER_PYTHON}" \
  "${LLMAO_PHASE12_ADAPTER:?set LLMAO_PHASE12_ADAPTER}" \
  "$EVE_WORKSPACE_ROOT" \
  "$EVE_SOLVER_ROOT" \
  "$EVE_EVAL_LOG_ROOT" \
  "${LLMAO_PROJECT_ROOT:?set LLMAO_PROJECT_ROOT}"
