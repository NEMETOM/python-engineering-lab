import os
import sys

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def before_scenario(context, scenario):
    context.handler = None
    context.session_manager = None
    context.raw = None
    context.parsed = None
    context.msg = None
