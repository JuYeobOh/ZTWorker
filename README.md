# zt-worker

Zero Trust 직원 트래픽 시뮬레이션 시스템의 **Worker CLI**입니다.

---

## Worker의 역할

- EBS 디렉터리(profile / results / logs)를 생성한다.
- `employee-agent` Docker 컨테이너를 실행하고 살아 있는지 감시한다.
- 죽은 컨테이너를 재시작한다.
- 컨테이너에 `EMPLOYEE_ID`, `LOCATION_ID`, `WORKER_GROUP` 등 환경변수를 주입한다.

## Worker가 **하지 않는** 것

- browser-use / Playwright / Chrome 실행
- GroupOffice / Nextcloud UI 조작
- Controller daily plan 해석 또는 task 실행
- 직원별 업무 상태 판단 (로그인 성공 여부, task 완료 여부 등)
- AWS 인프라 생성

> **컨테이너 내부의 `employee-agent`가 Controller API를 직접 호출해서 자기 plan을 가져가고 업무를 수행한다.**
> Worker는 컨테이너를 띄우는 bootstrap/supervisor 도구일 뿐이다.

---

## 설치

```bash
cd worker
pip install -e ".[dev]"
```

---

## 한 줄 실행 예시

**Enterprise HR 서브넷 EC2:**
```bash
zt-worker run \
  --mode enterprise \
  --location enterprise-hr \
  --controller-url http://controller.internal:8443```

**Enterprise 전체 12명 (location 생략):**
```bash
zt-worker run \
  --mode enterprise \
  --controller-url http://controller.internal:8443```

**Branch Dev 서브넷 EC2:**
```bash
zt-worker run \
  --mode branch \
  --location branch-dev \
  --controller-url http://controller.internal:8443```

**Cafe EC2 (location 필수):**
```bash
zt-worker run \
  --mode cafe \
  --location outdoor-cafe-1 \
  --controller-url http://controller.internal:8443```

**config 파일 사용:**
```bash
zt-worker run --config ./worker.yaml
```

---

## 명령어 목록

| 명령어 | 설명 |
|---|---|
| `zt-worker run` | setup 후 supervise loop 실행 (기본 장기실행 명령) |
| `zt-worker setup` | 디렉터리 생성 + 컨테이너 생성/시작 |
| `zt-worker supervise` | 컨테이너 감시 루프만 실행 |
| `zt-worker status` | 관리 중인 컨테이너 목록과 상태 출력 |
| `zt-worker stop` | 컨테이너 중지 (`--remove`로 삭제 가능) |
| `zt-worker restart-dead` | exited/dead 컨테이너만 재시작 |

---

## config 파일 예시

```yaml
worker_id: enterprise-hr-worker
mode: enterprise
location_id: enterprise-hr
controller_url: http://controller.internal:8443
data_root: /data/zt
employee_image: employee-agent:latest
restart_policy: unless-stopped
shm_size: 2g
supervise_interval_seconds: 30
```

전체 예시: [`config/worker.example.yaml`](config/worker.example.yaml)

> CLI 옵션이 config 파일보다 항상 우선한다.

---

## mode 설명

### enterprise
- `enterprise-hr`, `enterprise-sales`, `enterprise-finance` 3개 location, 총 12명
- `--location`을 지정하면 해당 location 4명만 실행
- `--location` 생략 시 전체 12명 실행, 각 직원의 `LOCATION_ID`는 home location 사용

### branch
- `branch-dev`, `branch-it` 2개 location, 총 8명
- `--location`을 지정하면 해당 location 4명만 실행
- `--location` 생략 시 전체 8명 실행

### cafe
- **`--location`이 필수** (`outdoor-cafe-1` / `outdoor-cafe-2`)
- enterprise + branch 전체 **20명 후보 컨테이너**를 모두 실행
- 실제로 로그인하는 직원은 Controller가 반환하는 plan에 따라 `employee-agent` 컨테이너가 스스로 판단
- Worker는 누가 카페 근무자인지 판단하지 않는다

---

## EBS 디렉터리 구조

```
/data/zt/
  profiles/
    {location_id}/
      {employee_id}/        ← /app/profile 으로 mount
  results/
    {location_id}/
      {employee_id}/        ← /app/results 으로 mount
  logs/
    {location_id}/
      {employee_id}/        ← /app/logs    으로 mount
```

예:
```
/data/zt/profiles/enterprise-hr/enter-hr-staff/
/data/zt/results/enterprise-hr/enter-hr-staff/
/data/zt/logs/enterprise-hr/enter-hr-staff/
```

---

## 컨테이너 환경변수

| 변수 | 설명 |
|---|---|
| `EMPLOYEE_ID` | 직원 식별자 (예: `enter-hr-staff`) |
| `LOCATION_ID` | 배치 location (예: `enterprise-hr`, `outdoor-cafe-1`) |
| `WORKER_GROUP` | 그룹 (enterprise / branch) |
| `CONTROLLER_URL` | Controller API 엔드포인트 |
| `PROFILE_DIR` | 브라우저 프로필 경로 (`/app/profile`) |
| `RESULTS_DIR` | 결과 저장 경로 (`/app/results`) |
| `LOG_DIR` | 로그 저장 경로 (`/app/logs`) |
| `TZ` | 시간대 (`Asia/Seoul`) |
| `BROWSER_HEADLESS` | 브라우저 headless 여부 (`true`) |
| `WORKER_ID` | (선택) Worker 식별자 |

---

## 컨테이너가 자기를 식별하는 방식

컨테이너 내부의 `employee-agent`는 시작 시 환경변수를 읽어 자기가 누구인지 파악한다:

```python
employee_id   = os.environ["EMPLOYEE_ID"]    # "enter-hr-staff"
location_id   = os.environ["LOCATION_ID"]    # "enterprise-hr"
worker_group  = os.environ["WORKER_GROUP"]   # "enterprise"
controller_url = os.environ["CONTROLLER_URL"]
```

그 후 Controller API에 `GET /plan?employee_id={employee_id}&location_id={location_id}` 형태로 요청해서 오늘의 업무 계획을 가져온다.

---

## cafe mode 동작 방식

cafe mode에서 Worker는 **전체 20명** 후보 컨테이너를 띄운다.

각 컨테이너는:
1. `LOCATION_ID=outdoor-cafe-1` (지정된 cafe location) 을 받는다.
2. Controller API에 직접 요청 → "오늘 outdoor-cafe-1에서 나(enter-hr-staff)는 근무하는가?"를 확인
3. 근무 대상이면 로그인하고 업무를 수행하고, 아니면 idle 상태를 유지한다.

Worker는 이 판단 과정에 관여하지 않는다.

---

## Docker 컨테이너 동작 규칙

- **포트 publish 없음** (`-p` 옵션 사용 금지)
- 모든 통신은 컨테이너 → Controller 방향 outbound only
- restart policy: `unless-stopped`
- shm size: `2g` (브라우저 메모리 확보)
- network mode: `bridge`

---

## 테스트 실행

```bash
cd worker
pytest
```

---

## EC2 배포 (systemd)

Worker는 **호스트에 직접** 설치한다 (컨테이너로 감싸지 않는다).
- Worker는 `/var/run/docker.sock`을 통해 Agent 컨테이너를 띄우는 부모 프로세스다.
- DinD나 socket mount는 사실상 호스트 root 권한이라 격리 이득이 없다.
- 호스트 EBS(`/data/zt/...`) 디렉터리도 직접 만든다.

### 1) Python venv에 zt-worker 설치

```bash
sudo dnf install -y git docker python3-pip
sudo systemctl enable --now docker

# /opt/zt-worker에 코드 + venv
sudo mkdir -p /opt/zt-worker
sudo chown $USER /opt/zt-worker
git clone <ZTWorker-repo> /opt/zt-worker
python3 -m venv /opt/zt-worker/.venv
/opt/zt-worker/.venv/bin/pip install -e /opt/zt-worker/worker
```

### 2) 설정 파일 작성

`worker.example.yaml`을 복사해 EC2의 `mode`/`location_id`에 맞춰 채운다.
**`llm_api_key`는 평문이므로 600 권한, root 소유 필수.**

```bash
sudo mkdir -p /etc/zt
sudo cp /opt/zt-worker/worker/config/worker.example.yaml /etc/zt/worker.yaml
sudo vim /etc/zt/worker.yaml          # mode/location_id/controller_url/llm_api_key 채움
sudo chmod 600 /etc/zt/worker.yaml
sudo chown root:root /etc/zt/worker.yaml
```

각 EC2의 `mode` / `location_id` 조합:

| EC2 | mode | location_id |
|---|---|---|
| Enterprise | enterprise | (생략 — 12명 모두 띄움) 또는 `enterprise-hr` / `enterprise-sales` / `enterprise-finance` |
| Branch | branch | (생략 — 8명 모두) 또는 `branch-dev` / `branch-it` |
| Cafe-1 | cafe | `outdoor-cafe-1` |
| Cafe-2 | cafe | `outdoor-cafe-2` |

### 3) Agent 이미지 준비

```bash
# 옵션 A: 호스트에서 docker build
git clone <ZTAgent-repo> /opt/zt-agent
docker build -t employee-agent:latest /opt/zt-agent/employee-agent

# 옵션 B: ECR/도커허브에서 pull
# docker pull <registry>/employee-agent:latest
# docker tag <registry>/employee-agent:latest employee-agent:latest
```

### 4) systemd unit 등록

```bash
sudo cp /opt/zt-worker/worker/deploy/zt-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zt-worker
sudo journalctl -u zt-worker -f                   # 로그 스트리밍
```

부팅 → systemd가 zt-worker 살림 → zt-worker가 Agent 컨테이너 띄움 → Agent 컨테이너는
`restart: unless-stopped`로 자체 살아남. 3중 안전망.

### 5) 운영 명령

```bash
sudo systemctl status zt-worker        # 워커 상태
sudo systemctl restart zt-worker       # 설정 변경 후 재시작
docker ps --filter name=zt-            # 살아있는 Agent 컨테이너 목록
docker logs zt-enterprise-hr-enter-hr-staff -f   # 특정 Agent 로그
```

### 시크릿 운영 메모

- `worker.yaml`은 git에 절대 커밋 금지(`.gitignore`에 패턴 등록됨).
- `.env`/`.env.*`/`*.env` 패턴도 무시된다.
- 운영 길어지면 AWS SSM Parameter Store / Secrets Manager로 이전 (Plan RFC-2).

---

## 결과·로그 S3 동기화 (매시간)

5일 수집 동안 EC2의 EBS에 누적되는 `results/`와 `logs/`를 매시간 S3로 incremental sync.
`profiles/`는 브라우저 세션 cache라 의도적으로 제외.

### 1) AWS 준비
- S3 버킷 생성 (예: `<your-s3-bucket>`).
- EC2 Instance Profile에 IAM 정책 부여:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:PutObject", "s3:GetObject"],
      "Resource": [
        "arn:aws:s3:::<your-s3-bucket>",
        "arn:aws:s3:::<your-s3-bucket>/*"
      ]
    }]
  }
  ```
- EC2에 `aws` CLI 설치 (Amazon Linux는 사전 설치, 필요 시 `dnf install -y awscli`).

### 2) 환경 파일 작성
```bash
sudo tee /etc/zt/sync.env >/dev/null <<'EOF'
ZT_S3_BUCKET=<your-s3-bucket>
ZT_S3_PREFIX=agent
EOF
sudo chmod 600 /etc/zt/sync.env
```

### 3) systemd unit·timer 등록
```bash
sudo cp /opt/zt-worker/worker/deploy/zt-sync-results.service /etc/systemd/system/
sudo cp /opt/zt-worker/worker/deploy/zt-sync-results.timer   /etc/systemd/system/
sudo chmod +x /opt/zt-worker/worker/deploy/zt-sync-results.sh
sudo systemctl daemon-reload
sudo systemctl enable --now zt-sync-results.timer
```

### 4) 동작 확인
```bash
systemctl list-timers | grep zt-sync                 # 다음 트리거 시각
sudo systemctl start zt-sync-results.service         # 즉시 1회 실행
journalctl -u zt-sync-results.service -n 100         # 결과 로그
aws s3 ls s3://<your-s3-bucket>/agent/results/ --recursive | head
```

### sync 정책 메모

- 대상: `results/`(스크린샷·trace·메타) + `logs/`(jsonl). `profiles/` 제외.
- `--delete` 미사용 — 호스트 파일 삭제가 S3에 전파되면 안 됨(보존 목적).
- 빈도: 매시간 + 0~3분 랜덤 지연 (EC2 4대 동시 sync 폭증 분산).
- `Persistent=true` — EC2 재부팅 후 직전에 누락된 trigger 1회 catch-up.
- S3 경로 구조: `s3://{bucket}/{prefix}/{kind}/{location_id}/{employee_id}/...`
