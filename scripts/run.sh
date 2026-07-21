#!/bin/bash
# 전날 미장 시황 브리핑: 파이프라인 실행 → data.json 갱신 → commit & push.
# launchd(평일 07:10 KST)가 호출. 로컬 수동 실행도 동일.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

# venv 있으면 사용, 없으면 시스템 python3
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
PY="${PYTHON:-python3}"

echo "[$(date '+%F %T')] run.sh start" >> brief.log
"$PY" scripts/pipeline.py --out data.json >> brief.log 2>&1

if ! git diff --quiet -- data.json; then
  git add data.json
  git commit -m "brief: $(date '+%F')" >> brief.log 2>&1
  git push >> brief.log 2>&1
  echo "[$(date '+%F %T')] pushed" >> brief.log
else
  echo "[$(date '+%F %T')] no change" >> brief.log
fi
