from edict.core.loader import load_strategy_class
from edict.core.strategy import Strategy


def test_load_demo_strategy():
    cls = load_strategy_class("edict.strategies.demo:DemoStrategy")
    assert issubclass(cls, Strategy)
