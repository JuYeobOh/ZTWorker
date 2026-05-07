#!/usr/bin/env bash
# Agent / Worker 배포 갱신 — SSM Run Command 수동 트리거 전용.
# (자동 폴링 타이머 없음. 5일 수집 중 컨테이너 무중단 보장을 위해 사용자가 명시 호출할 때만 동작.)
#
# 동작:
# - /opt/zt-agent + /opt/zt-worker git pull
# - Agent 변경 있으면 이미지 재빌드
# - Worker 변경 있으면 venv editable install 갱신 (의존성 변경 대비)
# - 변경 발생 OR --force 시: zt-worker stop → zt-* 컨테이너 강제 rm → start
#                            (supervise 루프이 30s 안에 새 이미지·새 yaml 로 컨테이너 재생성)
#
# SSM 사용 예:
#   aws ssm send-command --document-name AWS-RunShellScript \
#     --targets "Key=tag:Name,Values=hr,sales,fin,dev,it,outdoor1,outdoor2" \
#     --parameters '{"commands":["bash /opt/zt-worker/deploy/update-agent.sh"]}'
#
#   yaml만 바꾸고 강제 재배치할 때 (--force):
#     ... '{"commands":["bash /opt/zt-worker/deploy/update-agent.sh --force"]}'

set -euo pipefail

AGENT_DIR=/opt/zt-agent
WORKER_DIR=/opt/zt-worker
IMAGE=employee-agent:latest
WORKER_VENV_PIP=/opt/zt-worker/.venv/bin/pip

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

log() { echo "[update-agent $(date -Iseconds)] $*"; }

cd "$AGENT_DIR"
git fetch --quiet
AGENT_BEFORE=$(git rev-parse HEAD)
git pull --ff-only --quiet
AGENT_AFTER=$(git rev-parse HEAD)

cd "$WORKER_DIR"
git fetch --quiet
WORKER_BEFORE=$(git rev-parse HEAD)
git pull --ff-only --quiet
WORKER_AFTER=$(git rev-parse HEAD)

AGENT_CHANGED=0
WORKER_CHANGED=0
[[ "$AGENT_BEFORE"  != "$AGENT_AFTER"  ]] && AGENT_CHANGED=1
[[ "$WORKER_BEFORE" != "$WORKER_AFTER" ]] && WORKER_CHANGED=1

if [[ "$FORCE" -eq 0 && "$AGENT_CHANGED" -eq 0 && "$WORKER_CHANGED" -eq 0 ]]; then
  log "no changes (agent=${AGENT_AFTER:0:7} worker=${WORKER_AFTER:0:7}), exit 0"
  exit 0
fi

if [[ "$AGENT_CHANGED" -eq 1 ]]; then
  log "rebuilding agent image (${AGENT_BEFORE:0:7} -> ${AGENT_AFTER:0:7})"
  docker build -t "$IMAGE" "$AGENT_DIR"
fi

if [[ "$WORKER_CHANGED" -eq 1 ]]; then
  log "reinstalling worker venv (${WORKER_BEFORE:0:7} -> ${WORKER_AFTER:0:7})"
  "$WORKER_VENV_PIP" install -e "$WORKER_DIR" --quiet
fi

log "stopping zt-worker"
systemctl stop zt-worker || true

log "removing zt-* containers"
docker ps -aq --filter "name=zt-" | xargs -r docker rm -f || true

log "starting zt-worker"
systemctl start zt-worker

log "done. agent=${AGENT_AFTER:0:7} worker=${WORKER_AFTER:0:7} force=$FORCE"
