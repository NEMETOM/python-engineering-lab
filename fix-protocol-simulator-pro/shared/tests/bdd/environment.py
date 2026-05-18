import logging
import sys
from pathlib import Path

_here = Path(__file__).resolve()
_repo_root = str(_here.parent.parent.parent.parent)  # fix-protocol-simulator-pro/
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def before_scenario(context, scenario):
    logging.getLogger().handlers.clear()


def after_scenario(context, scenario):
    logging.getLogger().handlers.clear()
