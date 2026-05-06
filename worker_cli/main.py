from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from .config import build_config, WorkerConfig
from .docker_manager import DockerManager, container_name
from .employees import get_targets
from .supervisor import setup, supervise_loop, supervise_once, build_specs
from .status import print_status

app = typer.Typer(
    name="zt-worker",
    help="Zero Trust Worker — employee-agent container supervisor.",
    no_args_is_help=True,
)

# ── Shared options ──────────────────────────────────────────────────────────

def _common_options(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to worker.yaml"),
    mode: Optional[str] = typer.Option(None, "--mode", help="enterprise | branch | cafe"),
    location: Optional[str] = typer.Option(None, "--location", help="Location ID"),
    controller_url: Optional[str] = typer.Option(None, "--controller-url"),
    data_root: Optional[str] = typer.Option(None, "--data-root"),
    image: Optional[str] = typer.Option(None, "--image", help="employee-agent Docker image"),
    restart_policy: Optional[str] = typer.Option(None, "--restart-policy"),
    shm_size: Optional[str] = typer.Option(None, "--shm-size"),
    worker_id: Optional[str] = typer.Option(None, "--worker-id"),
) -> WorkerConfig:
    try:
        return build_config(
            config_file=config,
            mode=mode,
            location_id=location,
            controller_url=controller_url,
            data_root=data_root,
            employee_image=image,
            restart_policy=restart_policy,
            shm_size=shm_size,
            worker_id=worker_id,
        )
    except Exception as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(1)


# ── Commands ────────────────────────────────────────────────────────────────

@app.command()
def setup_cmd(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    mode: Optional[str] = typer.Option(None, "--mode"),
    location: Optional[str] = typer.Option(None, "--location"),
    controller_url: Optional[str] = typer.Option(None, "--controller-url"),
    data_root: Optional[str] = typer.Option(None, "--data-root"),
    image: Optional[str] = typer.Option(None, "--image"),
    restart_policy: Optional[str] = typer.Option(None, "--restart-policy"),
    shm_size: Optional[str] = typer.Option(None, "--shm-size"),
    worker_id: Optional[str] = typer.Option(None, "--worker-id"),
):
    """Create EBS directories and start employee-agent containers."""
    cfg = _load_cfg(config, mode, location, controller_url,
                    data_root, image, restart_policy, shm_size, worker_id)
    dm = DockerManager()
    setup(cfg, dm)


@app.command()
def supervise(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    mode: Optional[str] = typer.Option(None, "--mode"),
    location: Optional[str] = typer.Option(None, "--location"),
    controller_url: Optional[str] = typer.Option(None, "--controller-url"),
    data_root: Optional[str] = typer.Option(None, "--data-root"),
    image: Optional[str] = typer.Option(None, "--image"),
    restart_policy: Optional[str] = typer.Option(None, "--restart-policy"),
    shm_size: Optional[str] = typer.Option(None, "--shm-size"),
    worker_id: Optional[str] = typer.Option(None, "--worker-id"),
    interval: Optional[int] = typer.Option(None, "--interval", help="Override supervise interval (seconds)"),
):
    """Watch and restart dead containers in a loop."""
    cfg = _load_cfg(config, mode, location, controller_url,
                    data_root, image, restart_policy, shm_size, worker_id)
    if interval is not None:
        cfg = cfg.model_copy(update={"supervise_interval_seconds": interval})
    dm = DockerManager()
    supervise_loop(cfg, dm)


@app.command()
def run(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    mode: Optional[str] = typer.Option(None, "--mode"),
    location: Optional[str] = typer.Option(None, "--location"),
    controller_url: Optional[str] = typer.Option(None, "--controller-url"),
    data_root: Optional[str] = typer.Option(None, "--data-root"),
    image: Optional[str] = typer.Option(None, "--image"),
    restart_policy: Optional[str] = typer.Option(None, "--restart-policy"),
    shm_size: Optional[str] = typer.Option(None, "--shm-size"),
    worker_id: Optional[str] = typer.Option(None, "--worker-id"),
    interval: Optional[int] = typer.Option(None, "--interval"),
):
    """Run setup then enter the supervise loop (primary long-running command)."""
    cfg = _load_cfg(config, mode, location, controller_url,
                    data_root, image, restart_policy, shm_size, worker_id)
    if interval is not None:
        cfg = cfg.model_copy(update={"supervise_interval_seconds": interval})
    dm = DockerManager()
    setup(cfg, dm)
    supervise_loop(cfg, dm)


@app.command()
def status(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    mode: Optional[str] = typer.Option(None, "--mode"),
    location: Optional[str] = typer.Option(None, "--location"),
    controller_url: Optional[str] = typer.Option(None, "--controller-url"),
    data_root: Optional[str] = typer.Option(None, "--data-root"),
    image: Optional[str] = typer.Option(None, "--image"),
    worker_id: Optional[str] = typer.Option(None, "--worker-id"),
):
    """Show managed containers and their current state."""
    cfg = _load_cfg(config, mode, location, controller_url,
                    data_root, image, None, None, worker_id)
    dm = DockerManager()
    print_status(cfg, dm)


@app.command()
def stop(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    mode: Optional[str] = typer.Option(None, "--mode"),
    location: Optional[str] = typer.Option(None, "--location"),
    controller_url: Optional[str] = typer.Option(None, "--controller-url"),
    data_root: Optional[str] = typer.Option(None, "--data-root"),
    image: Optional[str] = typer.Option(None, "--image"),
    worker_id: Optional[str] = typer.Option(None, "--worker-id"),
    remove: bool = typer.Option(False, "--remove", help="Also remove containers (data is kept)"),
):
    """Stop this worker's containers. Data directories are never deleted."""
    cfg = _load_cfg(config, mode, location, controller_url,
                    data_root, image, None, None, worker_id)
    dm = DockerManager()
    targets = get_targets(cfg.mode, cfg.location_id)
    names = [container_name(t.location_id, t.employee.employee_id) for t in targets]
    dm.stop_containers(names, remove=remove)
    verb = "removed" if remove else "stopped"
    print(f"[stop] {len(names)} containers {verb}.")


@app.command(name="restart-dead")
def restart_dead(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    mode: Optional[str] = typer.Option(None, "--mode"),
    location: Optional[str] = typer.Option(None, "--location"),
    controller_url: Optional[str] = typer.Option(None, "--controller-url"),
    data_root: Optional[str] = typer.Option(None, "--data-root"),
    image: Optional[str] = typer.Option(None, "--image"),
    worker_id: Optional[str] = typer.Option(None, "--worker-id"),
):
    """Restart only exited/dead containers; leave running ones alone."""
    cfg = _load_cfg(config, mode, location, controller_url,
                    data_root, image, None, None, worker_id)
    dm = DockerManager()
    specs = build_specs(cfg)
    names = list(specs.keys())
    restarted = dm.restart_dead(names, specs)
    if restarted:
        for n in restarted:
            print(f"[restart-dead] restarted: {n}")
    else:
        print("[restart-dead] No dead containers found.")


# ── Helper ──────────────────────────────────────────────────────────────────

def _load_cfg(
    config: Optional[Path],
    mode: Optional[str],
    location: Optional[str],
    controller_url: Optional[str],
    data_root: Optional[str],
    image: Optional[str],
    restart_policy: Optional[str],
    shm_size: Optional[str],
    worker_id: Optional[str],
) -> WorkerConfig:
    try:
        return build_config(
            config_file=config,
            mode=mode,
            location_id=location,
            controller_url=controller_url,
            data_root=data_root,
            employee_image=image,
            restart_policy=restart_policy,
            shm_size=shm_size,
            worker_id=worker_id,
        )
    except Exception as exc:
        typer.echo(f"[error] {exc}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
