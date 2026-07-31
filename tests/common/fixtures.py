"""Reusable fixture factories.

The module intentionally contains factories rather than auto-loaded fixtures;
test modules opt in explicitly and remain easy to understand.
"""
from __future__ import annotations

from core.testing import FakeComponent


def make_fake_component(*args, **kwargs):
    return FakeComponent(*args, **kwargs)
