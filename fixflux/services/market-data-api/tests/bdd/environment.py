import os
import sys
from contextlib import ExitStack

_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
for _p in (_repo_root, _src):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def before_scenario(context, scenario):
    # Everything a scenario opens (Kafka patch, app lifespan, WebSocket
    # sessions) is registered here, so it is torn down even when a step fails.
    # The app's ConnectionManager is a module-level singleton, so a leaked
    # socket would otherwise carry into the next scenario.
    context.stack = ExitStack()


def after_scenario(context, scenario):
    context.stack.close()
