from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Type

from .strategy import Strategy


@dataclass(frozen=True)
class StrategySpec:
    module: str
    symbol: str


def load_strategy_class(spec: str) -> Type[Strategy]:
    """Load a Strategy class from 'module.path:ClassName'."""

    if ":" not in spec:
        raise ValueError("Strategy spec must be in form 'module:ClassName'")

    mod_name, cls_name = spec.split(":", 1)
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name, None)
    if cls is None:
        raise ValueError(f"Strategy class not found: {spec}")

    if not isinstance(cls, type) or not issubclass(cls, Strategy):
        raise TypeError(f"{spec} is not a Strategy subclass")

    return cls
