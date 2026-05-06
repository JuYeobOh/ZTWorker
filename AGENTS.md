# AGENTS.md — zt-worker 에이전트 가이드

이 문서는 다른 에이전트가 zt-worker 코드베이스를 이해하고 수정할 때 참고하는 가이드다.

---

## 이 프로젝트가 하는 일 (한 줄 요약)

> **employee-agent Docker 컨테이너를 mode/location 설정에 따라 생성·감시·재시작하는 supervisor CLI 도구.**

Worker는 컨테이너 내부 동작(browser-use, 로그인, task 수행)에 전혀 관여하지 않는다.  
컨테이너에 환경변수를 주입하고, 살아 있는지 확인하고, 죽으면 다시 띄우는 것이 전부다.

---

## 모듈 구조와 역할

```
worker_cli/
  config.py        ← 설정의 단일 진입점
  employees.py     ← mode/location → 직원 목록 계산 (순수 함수)
  filesystem.py    ← EBS 경로 계산 + 디렉터리 생성
  docker_manager.py ← Docker SDK 래핑. ContainerSpec 생성 및 컨테이너 조작
  supervisor.py    ← setup / supervise loop 오케스트레이션
  status.py        ← status 명령 출력 포맷
  main.py          ← Typer CLI 정의 (6개 명령)
```

### 데이터 흐름

```
CLI 인자 + YAML
      │
      ▼
 config.py (WorkerConfig)
      │
      ├─► employees.py (get_targets)
      │         │ List[EmployeeTarget]
      │         ▼
      ├─► filesystem.py (employee_paths → ensure_directories)
      │         │ EmployeePaths
      │         ▼
      └─► docker_manager.py (build_spec → ensure_container)
                │
                ▼
         Docker daemon
```

---

## 핵심 타입

### `WorkerConfig` (`config.py`)
Pydantic 모델. 모든 설정의 중심.

| 필드 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `mode` | `"enterprise"/"branch"/"cafe"` | 필수 | 실행 모드 |
| `location_id` | `str \| None` | None | cafe는 필수 |
| `controller_url` | `str` | 필수 | Controller API URL |
| `data_root` | `str` | `/data/zt` | EBS 마운트 루트 |
| `employee_image` | `str` | `employee-agent:latest` | Docker 이미지 |
| `restart_policy` | `str` | `unless-stopped` | Docker restart policy |
| `shm_size` | `str` | `2g` | 컨테이너 shm |
| `supervise_interval_seconds` | `int` | `30` | supervise 주기 |

### `Employee` (`employees.py`)
```python
@dataclass(frozen=True)
class Employee:
    employee_id: str      # "enter-hr-staff"
    home_location: str    # "enterprise-hr"
    worker_group: str     # "enterprise"
```

### `EmployeeTarget` (`employees.py`)
Employee + 이번 배포에서 사용할 location_id.  
cafe mode에서는 `location_id != employee.home_location`이 될 수 있다.

```python
@dataclass(frozen=True)
class EmployeeTarget:
    employee: Employee
    location_id: str   # cafe면 "outdoor-cafe-1" 등
```

### `ContainerSpec` (`docker_manager.py`)
`build_spec()`이 만들어주는 컨테이너 실행 파라미터 묶음.  
`ports` 필드가 없다 — 의도적으로 port publish를 차단하는 설계다.

### `EmployeePaths` (`filesystem.py`)
```python
@dataclass(frozen=True)
class EmployeePaths:
    profile: Path   # /data/zt/profiles/{location_id}/{employee_id}
    results: Path   # /data/zt/results/{location_id}/{employee_id}
    logs:    Path   # /data/zt/logs/{location_id}/{employee_id}
```

---

## 직원 목록 계산 규칙 (`employees.py`)

`get_targets(mode, location_id)` 한 함수가 모든 경우를 처리한다.

| mode | location_id | 결과 |
|---|---|---|
| enterprise | enterprise-hr | HR 4명, location_id=enterprise-hr |
| enterprise | enterprise-sales | Sales 4명 |
| enterprise | enterprise-finance | Finance 4명 |
| enterprise | None | 전체 12명, 각자 home_location 사용 |
| branch | branch-dev | Dev 4명 |
| branch | branch-it | IT 4명 |
| branch | None | 전체 8명 |
| cafe | outdoor-cafe-1 | 전체 20명, location_id=outdoor-cafe-1 |
| cafe | outdoor-cafe-2 | 전체 20명, location_id=outdoor-cafe-2 |
| cafe | None | **ValueError** (cafe는 location 필수) |

cafe 후보 20명 = enterprise 12명 + branch 8명 전원.

---

## container 이름 규칙

```
zt-{location_id}-{employee_id}
```

예:
- `zt-enterprise-hr-enter-hr-staff`
- `zt-outdoor-cafe-1-enter-hr-staff`  ← 같은 직원이지만 이름이 다름

같은 직원이 home EC2와 cafe EC2에 동시에 컨테이너로 존재할 수 있으므로  
location_id가 반드시 이름에 포함되어야 한다.

---

## supervise loop 동작

`supervisor.py::supervise_loop(cfg, dm)` 이 무한 루프다.

매 `supervise_interval_seconds`마다:
1. `build_specs(cfg)` → 관리해야 할 ContainerSpec dict 계산
2. 각 spec에 대해 `dm.ensure_container(spec)` 호출
   - container 없음 → `run_container()` (새로 생성)
   - `exited` / `dead` / `created` → `container.start()` (재시작)
   - `running` → 아무것도 안 함
3. 변화가 있을 때만 로그 출력

Worker는 컨테이너 내부에서 무슨 일이 벌어지는지 확인하지 않는다.

---

## Docker 불변 규칙

`docker_manager.py::run_container()` 에서 강제한다:

```python
ports={}   # 항상 빈 dict — port publish 절대 금지
```

이 줄을 제거하거나 실제 포트를 추가하면 안 된다.  
모든 통신은 컨테이너 → Controller 방향 outbound only다.

---

## 환경변수 주입 (`docker_manager.py::build_spec`)

컨테이너에 전달되는 환경변수:

| 변수 | 값 출처 |
|---|---|
| `EMPLOYEE_ID` | `target.employee.employee_id` |
| `LOCATION_ID` | `target.location_id` (cafe면 cafe location) |
| `WORKER_GROUP` | `target.employee.worker_group` |
| `CONTROLLER_URL` | `cfg.controller_url` |
| `PROFILE_DIR` | `/app/profile` (고정) |
| `RESULTS_DIR` | `/app/results` (고정) |
| `LOG_DIR` | `/app/logs` (고정) |
| `TZ` | `Asia/Seoul` (고정) |
| `BROWSER_HEADLESS` | `true` (고정) |
| `WORKER_ID` | `cfg.worker_id` (설정된 경우만) |

---

## 설정 우선순위

```
CLI 옵션 > worker.yaml > Pydantic 기본값
```

`build_config()` 가 병합을 담당한다.  
CLI 옵션이 `None`이면 config 값을 덮어쓰지 않는다.

---

## 테스트 구조

Docker daemon 없이 전부 통과한다. Docker SDK를 직접 호출하는 코드는 테스트에서 실행하지 않는다.

| 파일 | 검증 대상 |
|---|---|
| `test_employee_selection.py` | `get_targets()` 반환 목록 수/내용 |
| `test_container_naming.py` | `container_name()` 포맷, location 포함 여부 |
| `test_volume_paths.py` | `employee_paths()` 경로 구조 |
| `test_docker_run_config.py` | `build_spec()` 환경변수·volume·port 없음·restart·shm |
| `test_config_loading.py` | YAML 로딩, CLI override, 기본값, validation |

테스트 실행:
```bash
cd worker
pytest
```

---

## 수정할 때 주의사항

1. **직원 추가/제거** → `employees.py` 의 해당 리스트만 수정하면 된다. 다른 파일은 건드릴 필요 없다.
2. **location 추가/제거** → `employees.py` 의 `VALID_*_LOCATIONS` 와 `*_LOCATION_MAP` 수정 + 관련 테스트 수정.
3. **환경변수 추가** → `docker_manager.py::build_spec()` 의 `env` dict에 추가.
4. **포트 publish 금지** → `run_container()` 의 `ports={}` 절대 변경하지 말 것.
5. **새 CLI 명령 추가** → `main.py` 에 `@app.command()` 추가, `_load_cfg()` helper 재사용.
