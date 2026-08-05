"""Semantic chunker – splits markdown text into overlapping chunks."""

from __future__ import annotations

import re
from typing import Any


class SemanticChunker:
    """Split text on paragraph/heading boundaries, fall back to character windows."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100) -> None:
        self._size = chunk_size
        self._overlap = chunk_overlap

    def chunk(self, text: str) -> list[dict[str, Any]]:
        segments = self._split_by_structure(text)
        return self._merge_into_chunks(segments)

    def _split_by_structure(self, text: str) -> list[str]:
        parts = re.split(r"\n{2,}", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _merge_into_chunks(self, segments: list[str]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        current_parts: list[str] = []
        current_len = 0
        overlap_buffer: list[str] = []

        for seg in segments:
            seg_len = len(seg)

            if current_len + seg_len > self._size and current_parts:
                content = "\n\n".join(current_parts)
                chunks.append({"content": content, "metadata": {"source_type": "semantic"}})
                overlap_buffer = self._build_overlap(current_parts)
                current_parts = list(overlap_buffer)
                current_len = sum(len(p) for p in current_parts)

            if seg_len > self._size:
                if current_parts:
                    content = "\n\n".join(current_parts)
                    chunks.append({"content": content, "metadata": {}})
                    current_parts = []
                    current_len = 0
                for window_chunk in self._sliding_window(seg):
                    chunks.append(window_chunk)
            else:
                current_parts.append(seg)
                current_len += seg_len

        if current_parts:
            chunks.append({"content": "\n\n".join(current_parts), "metadata": {}})

        return chunks if chunks else [{"content": text[:self._size], "metadata": {}}]

    def _build_overlap(self, parts: list[str]) -> list[str]:
        overlap: list[str] = []
        length = 0
        for part in reversed(parts):
            if length + len(part) > self._overlap:
                break
            overlap.insert(0, part)
            length += len(part)
        return overlap

    def _sliding_window(self, text: str) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        start = 0
        while start < len(text):
            end = start + self._size
            chunks.append({"content": text[start:end], "metadata": {}})
            start += self._size - self._overlap
        return chunks
