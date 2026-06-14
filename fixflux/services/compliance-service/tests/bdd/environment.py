import os
import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parent.parent.parent / "src")
_repo_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)

for _p in (_src, _repo_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/testdb")
