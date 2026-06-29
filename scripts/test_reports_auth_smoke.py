from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.deps import get_current_admin  # noqa: E402
from app.routers import reports  # noqa: E402


def main() -> None:
    dependencies = [dependency.dependency for dependency in reports.router.dependencies]
    assert get_current_admin in dependencies
    assert reports.router.prefix == "/api/reports"
    print("reports auth smoke passed")


if __name__ == "__main__":
    main()
