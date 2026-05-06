#!/usr/bin/env bash
# ZeroTrust Worker EC2 부트스트랩 스크립트.
# 빈 Amazon Linux EC2에서 한 번 실행하면 zt-worker가 systemd로 살아남는다.
#
# 사용법:
#   sudo MODE=enterprise LOCATION=enterprise-hr WORKER_ID=enterprise-hr-worker \
#        LLM_API_KEY=sk-proj-... bash bootstrap-worker.sh
#
#   또는 환경변수를 미리 export 해두고 sudo -E bash bootstrap-worker.sh

set -euo pipefail

# ── 입력 검증 ────────────────────────────────────────────────
: "${MODE:?MODE not set (enterprise / branch / cafe)}"
: "${LOCATION:?LOCATION not set (e.g. enterprise-hr)}"
: "${WORKER_ID:?WORKER_ID not set (e.g. enterprise-hr-worker)}"
: "${LLM_API_KEY:?LLM_API_KEY not set}"
: "${CONTROLLER_URL:?CONTROLLER_URL not set (e.g. http://10.0.0.10:8443 — VPC private)}"
: "${S3_BUCKET:?S3_BUCKET not set}"
: "${GIT_USER:?GIT_USER not set (GitHub username for repos)}"

S3_PREFIX="${S3_PREFIX:-agent}"

echo "==[1/7] 패키지 설치"
# Amazon Linux 2023 기본 python은 3.9 — pyproject가 3.11+ 요구이므로 python3.11 별도 설치.
dnf install -y git docker python3.11 python3.11-pip

echo "==[2/7] Docker 데몬 + Compose/Buildx 플러그인"
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
if [[ ! -x /usr/local/lib/docker/cli-plugins/docker-compose ]]; then
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi
if [[ ! -x /usr/local/lib/docker/cli-plugins/docker-buildx ]]; then
    curl -SL https://github.com/docker/buildx/releases/download/v0.18.0/buildx-v0.18.0.linux-amd64 \
        -o /usr/local/lib/docker/cli-plugins/docker-buildx
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
fi

echo "==[3/7] ZTWorker 코드 + venv"
mkdir -p /opt /etc/zt
if [[ ! -d /opt/zt-worker/.git ]]; then
    git clone "https://github.com/${GIT_USER}/ZTWorker.git" /opt/zt-worker
fi
# python3.11 venv (pyproject가 3.11+ 요구)
if [[ ! -x /opt/zt-worker/.venv/bin/python3.11 ]]; then
    rm -rf /opt/zt-worker/.venv
    python3.11 -m venv /opt/zt-worker/.venv
fi
/opt/zt-worker/.venv/bin/pip install --upgrade pip
/opt/zt-worker/.venv/bin/pip install -e /opt/zt-worker
ln -sf /opt/zt-worker/.venv/bin/zt-worker /usr/local/bin/zt-worker

echo "==[4/7] Agent 이미지 빌드"
if [[ ! -d /opt/zt-agent/.git ]]; then
    git clone "https://github.com/${GIT_USER}/ZTAgent.git" /opt/zt-agent
fi
docker build -t employee-agent:latest /opt/zt-agent

echo "==[5/7] systemd unit + sync 스크립트 권한"
cp /opt/zt-worker/deploy/zt-worker.service       /etc/systemd/system/
cp /opt/zt-worker/deploy/zt-sync-results.service /etc/systemd/system/
cp /opt/zt-worker/deploy/zt-sync-results.timer   /etc/systemd/system/
chmod +x /opt/zt-worker/deploy/zt-sync-results.sh

echo "==[6/7] /etc/zt/worker.yaml + sync.env"
cat > /etc/zt/worker.yaml <<EOF
worker_id: ${WORKER_ID}
mode: ${MODE}
location_id: ${LOCATION}
controller_url: ${CONTROLLER_URL}
llm_api_key: ${LLM_API_KEY}
data_root: /data/zt
employee_image: employee-agent:latest
restart_policy: unless-stopped
shm_size: 2g
supervise_interval_seconds: 30
EOF
chmod 600 /etc/zt/worker.yaml
chown root:root /etc/zt/worker.yaml

cat > /etc/zt/sync.env <<EOF
ZT_S3_BUCKET=${S3_BUCKET}
ZT_S3_PREFIX=${S3_PREFIX}
EOF
chmod 600 /etc/zt/sync.env

echo "==[7/7] systemd 등록·시작"
systemctl daemon-reload
systemctl enable --now zt-worker zt-sync-results.timer

echo
echo "── DONE ── ${WORKER_ID} (${MODE}/${LOCATION})"
echo "확인:"
echo "  systemctl status zt-worker --no-pager"
echo "  docker ps --filter name=zt-"
echo "  journalctl -u zt-worker -n 30 --no-pager"
