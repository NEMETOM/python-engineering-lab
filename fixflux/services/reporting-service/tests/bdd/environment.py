import os
import sys

_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
for _p in (_repo_root, _src):
    if _p not in sys.path:
        sys.path.insert(0, _p)
