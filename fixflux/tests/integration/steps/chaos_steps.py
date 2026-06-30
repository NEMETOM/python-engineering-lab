import subprocess
import time
from pathlib import Path

from behave import given, when

_here = Path(__file__).resolve()
_compose_dir = _here.parent.parent.parent.parent  # fixflux/


def _compose(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=str(_compose_dir),
        capture_output=True,
        text=True,
    )


def _wait_for_running(service: str, timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = _compose("ps", service)
        if result.returncode == 0 and "running" in result.stdout.lower():
            time.sleep(3)  # grace period for Kafka consumer to initialise
            return
        time.sleep(3)
    raise AssertionError(
        f'"{service}" did not reach running state within {timeout}s after restart.\n'
        f"docker compose ps output:\n{result.stdout}"
    )


@given('the "{service}" container is stopped')
def step_stop_container(context, service):
    result = _compose("stop", service)
    assert result.returncode == 0, (
        f'Failed to stop "{service}": {result.stderr}'
    )
    if not hasattr(context, "chaos_stopped_services"):
        context.chaos_stopped_services = set()
    context.chaos_stopped_services.add(service)
    time.sleep(2)  # allow container to reach stopped state before submitting orders


@when('the "{service}" container is restarted')
def step_restart_container(context, service):
    result = _compose("start", service)
    assert result.returncode == 0, (
        f'Failed to start "{service}": {result.stderr}'
    )
    if hasattr(context, "chaos_stopped_services"):
        context.chaos_stopped_services.discard(service)
    _wait_for_running(service)
