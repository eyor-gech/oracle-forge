from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_current_dir = Path(__file__).resolve().parent
_legacy_planner_path = _current_dir.parent / "planner.py"

_spec = importlib.util.spec_from_file_location("agent._legacy_planner_module", str(_legacy_planner_path))
if _spec is None or _spec.loader is None:
    raise ImportError(f"Unable to load planner module from {_legacy_planner_path}")
_module = importlib.util.module_from_spec(_spec)
sys.modules["agent._legacy_planner_module"] = _module
_spec.loader.exec_module(_module)

PlanStep = _module.PlanStep
QueryPlanner = _module.QueryPlanner

__all__ = ["PlanStep", "QueryPlanner"]

