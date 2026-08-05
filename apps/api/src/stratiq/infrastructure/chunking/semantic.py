def chunk_markdown(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """Split markdown into overlapping character windows on paragraph boundaries when possible."""
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            flush()
        if len(para) <= chunk_size:
            current = para
            continue
        start = 0
        while start < len(para):
            end = min(start + chunk_size, len(para))
            piece = para[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(para):
                break
            start = max(end - overlap, start + 1)

    flush()

    if overlap > 0 and len(chunks) > 1:
        with_overlap: list[str] = [chunks[0]]
        for index in range(1, len(chunks)):
            prev_tail = chunks[index - 1][-overlap:]
            merged = f"{prev_tail}\n{chunks[index]}".strip()
            with_overlap.append(merged[: chunk_size + overlap])
        return with_overlap
    return chunks
