"""Base parser interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentParser(Protocol):
    """Convert raw file bytes to a markdown string."""

    def parse(self, data: bytes) -> str: ...
