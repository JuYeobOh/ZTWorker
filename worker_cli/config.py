from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, field_validator, model_validator


Mode = Literal["enterprise", "branch", "cafe"]


class WorkerConfig(BaseModel):
    worker_id: Optional[str] = None
    mode: Mode
    location_id: Optional[str] = None
    controller_url: str
    llm_api_key: str
    data_root: str = "/data/zt"
    employee_image: str = "employee-agent:latest"
    restart_policy: str = "unless-stopped"
    shm_size: str = "2g"
    supervise_interval_seconds: int = 30

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"enterprise", "branch", "cafe"}
        if v not in allowed:
            raise ValueError(f"mode must be one of {allowed}, got '{v}'")
        return v

    @model_validator(mode="after")
    def validate_cafe_requires_location(self) -> "WorkerConfig":
        if self.mode == "cafe" and not self.location_id:
            raise ValueError("cafe mode requires --location")
        return self


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_config(
    config_file: Optional[Path] = None,
    *,
    mode: Optional[str] = None,
    location_id: Optional[str] = None,
    controller_url: Optional[str] = None,
    llm_api_key: Optional[str] = None,
    data_root: Optional[str] = None,
    employee_image: Optional[str] = None,
    restart_policy: Optional[str] = None,
    shm_size: Optional[str] = None,
    supervise_interval_seconds: Optional[int] = None,
    worker_id: Optional[str] = None,
) -> WorkerConfig:
    base: dict = {}
    if config_file is not None:
        base = _load_yaml(config_file)

    # CLI options override config file (skip None values).
    # NOTE: llm_api_key는 CLI 옵션으로 노출되지 않는다 (평문 노출 방지).
    # 운영 시에는 worker.yaml에서만 읽힘.
    overrides = {
        "mode": mode,
        "location_id": location_id,
        "controller_url": controller_url,
        "llm_api_key": llm_api_key,
        "data_root": data_root,
        "employee_image": employee_image,
        "restart_policy": restart_policy,
        "shm_size": shm_size,
        "supervise_interval_seconds": supervise_interval_seconds,
        "worker_id": worker_id,
    }
    for k, v in overrides.items():
        if v is not None:
            base[k] = v

    return WorkerConfig(**base)
