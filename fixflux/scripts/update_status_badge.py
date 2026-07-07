#!/usr/bin/env python3
"""Read a Prometheus /api/v1/query?query=up JSON snapshot and update the
system-status badge in README.md between sentinel comment tags.

Usage:
    python3 update_status_badge.py <prom_data.json> <README.md>

The script is intentionally dependency-free (stdlib only) so it runs on the
bare GitHub Actions ubuntu-latest runner without any pip install step.
"""

import json
import re
import sys
from pathlib import Path

# Services that must ALL be up for "Healthy" status.
# These match the job_name values in prometheus.yml.
CORE_SERVICES = {"fix-gateway", "matching-engine", "trade-store"}

BADGE_COLORS = {
    "Healthy":  "brightgreen",
    "Degraded": "orange",
    "Down":     "red",
    "Unknown":  "lightgrey",
}

SENTINEL_START = "<!-- STATUS_BADGE_START -->"
SENTINEL_END   = "<!-- STATUS_BADGE_END -->"


def parse_status(prom_json: dict) -> tuple[str, list[str]]:
    """Return (overall_status, list_of_down_services)."""
    results = prom_json.get("data", {}).get("result", [])
    if not results:
        return "Unknown", list(CORE_SERVICES)

    up_by_job = {
        r["metric"].get("job", ""): float(r["value"][1])
        for r in results
        if "job" in r.get("metric", {}) and len(r.get("value", [])) == 2
    }

    down = sorted(svc for svc in CORE_SERVICES if up_by_job.get(svc, 0.0) < 1.0)

    if not down:
        return "Healthy", []
    if len(down) < len(CORE_SERVICES):
        return "Degraded", down
    return "Down", down


def badge_markdown(status: str, down: list[str]) -> str:
    color = BADGE_COLORS.get(status, "lightgrey")
    badge_url = (
        f"https://img.shields.io/badge/Live%20System-{status}-{color}"
        "?style=flat-square&logo=prometheus"
    )
    detail = f"Down: {', '.join(down)}" if down else "All core services operational"
    return (
        f"{SENTINEL_START}\n"
        f"[![Live System Status]({badge_url})](https://github.com/NEMETOM/python-engineering-lab)"
        f"  <!-- {detail} -->\n"
        f"{SENTINEL_END}"
    )


def update_readme(readme_path: Path, status: str, down: list[str]) -> bool:
    """Replace content between sentinels. Returns True if the file changed."""
    content = readme_path.read_text(encoding="utf-8")
    replacement = badge_markdown(status, down)
    pattern = re.compile(
        re.escape(SENTINEL_START) + r".*?" + re.escape(SENTINEL_END),
        re.DOTALL,
    )
    if pattern.search(content):
        new_content = pattern.sub(replacement, content)
    else:
        # Sentinels not found - insert after the first badge line block
        # (right before the first '---' separator)
        new_content = re.sub(
            r"(\n---\n)", f"\n{replacement}\n\\1", content, count=1
        )

    if new_content == content:
        return False
    readme_path.write_text(new_content, encoding="utf-8")
    return True


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <prom_data.json> <README.md>", file=sys.stderr)
        return 2

    prom_file = Path(sys.argv[1])
    readme_file = Path(sys.argv[2])

    try:
        prom_json = json.loads(prom_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Warning: could not parse {prom_file}: {exc}", file=sys.stderr)
        prom_json = {}

    status, down = parse_status(prom_json)
    changed = update_readme(readme_file, status, down)

    print(f"System status : {status}")
    if down:
        print(f"Services down : {', '.join(down)}")
    else:
        print("Services down : none")
    print(f"README updated: {'yes' if changed else 'no change'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
