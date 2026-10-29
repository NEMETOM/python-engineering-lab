import os
import sys

_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# src as well as the repo root, so the suite runs without a prior pip install
# (same setup as trade-store's tests/bdd/environment.py).
for _p in (_repo_root, _src):
    if _p not in sys.path:
        sys.path.insert(0, _p)
