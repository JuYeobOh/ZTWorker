#!/usr/bin/env bash
# ZeroTrust 결과/로그를 S3에 incremental sync한다.
# systemd timer(zt-sync-results.timer)가 매시간 호출.
#
# 환경 변수 (EnvironmentFile=/etc/zt/sync.env 권장):
#   ZT_S3_BUCKET   필수. 대상 S3 버킷 이름.
#   ZT_S3_PREFIX   선택. 기본 "zt".  s3://{bucket}/{prefix}/{kind}/{loc}/{eid}/...
#   ZT_DATA_ROOT   선택. 기본 /data/zt
#
# IAM (EC2 Instance Profile에 부여):
#   s3:ListBucket, s3:PutObject, s3:GetObject  on  arn:aws:s3:::{bucket}[/*]
#
# 의도적으로 sync 제외:
#   - profiles/ : 브라우저 세션 cache, 다음 부팅 시 재사용. 외부 보관 가치 없음.
#   - --delete  : 호스트 파일 삭제가 S3에 전파되면 안 됨(보존 목적).

set -euo pipefail

S3_BUCKET="${ZT_S3_BUCKET:?ZT_S3_BUCKET not set in /etc/zt/sync.env}"
S3_PREFIX="${ZT_S3_PREFIX:-zt}"
DATA_ROOT="${ZT_DATA_ROOT:-/data/zt}"

for kind in results logs; do
    src="${DATA_ROOT}/${kind}/"
    dst="s3://${S3_BUCKET}/${S3_PREFIX}/${kind}/"

    if [[ ! -d "$src" ]]; then
        # 디렉터리가 아직 없으면 (Worker 첫 부팅 직후 등) 조용히 skip.
        continue
    fi

    aws s3 sync "$src" "$dst" \
        --no-progress \
        --only-show-errors
done
