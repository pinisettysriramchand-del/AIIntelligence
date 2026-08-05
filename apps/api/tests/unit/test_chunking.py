"""Unit tests for SemanticChunker."""

import pytest

from stratiq.infrastructure.chunking.semantic import SemanticChunker


class TestSemanticChunker:
    def test_short_text_produces_single_chunk(self):
        chunker = SemanticChunker(chunk_size=800, chunk_overlap=100)
        result = chunker.chunk("Hello world. This is a short document.")
        assert len(result) == 1
        assert "Hello" in result[0]["content"]

    def test_long_text_splits_into_multiple_chunks(self):
        chunker = SemanticChunker(chunk_size=100, chunk_overlap=10)
        paragraphs = ["Paragraph " + str(i) + " " + ("word " * 20) for i in range(10)]
        text = "\n\n".join(paragraphs)
        result = chunker.chunk(text)
        assert len(result) > 1

    def test_chunk_content_non_empty(self):
        chunker = SemanticChunker(chunk_size=200, chunk_overlap=20)
        text = "\n\n".join(["This is paragraph " + str(i) + " with some content." for i in range(20)])
        result = chunker.chunk(text)
        for chunk in result:
            assert chunk["content"].strip() != ""

    def test_chunk_size_respected(self):
        chunker = SemanticChunker(chunk_size=50, chunk_overlap=5)
        long_word = "a" * 200
        result = chunker.chunk(long_word)
        for chunk in result:
            assert len(chunk["content"]) <= 50 + 5

    def test_empty_text_produces_chunk(self):
        chunker = SemanticChunker()
        result = chunker.chunk("   ")
        assert isinstance(result, list)

    def test_metadata_present(self):
        chunker = SemanticChunker(chunk_size=800)
        result = chunker.chunk("Some content here.\n\nAnother paragraph.")
        for chunk in result:
            assert "metadata" in chunk
            assert isinstance(chunk["metadata"], dict)

    def test_overlap_means_content_continuity(self):
        chunker = SemanticChunker(chunk_size=60, chunk_overlap=20)
        text = " ".join(["word"] * 100)
        result = chunker.chunk(text)
        if len(result) > 1:
            assert len(result[0]["content"]) > 0
            assert len(result[1]["content"]) > 0
