from pathlib import Path

import aiofiles


class LocalObjectStorage:
    """Filesystem object storage with an S3-shaped put/get/delete interface."""

    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not str(path).startswith(str(self._root.resolve())):
            raise ValueError("Invalid storage key")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as handle:
            await handle.write(data)
        meta = path.with_suffix(path.suffix + ".content_type")
        async with aiofiles.open(meta, "w", encoding="utf-8") as handle:
            await handle.write(content_type)
        return key

    async def get(self, key: str) -> bytes:
        path = self._path(key)
        async with aiofiles.open(path, "rb") as handle:
            return await handle.read()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()
        meta = path.with_suffix(path.suffix + ".content_type")
        if meta.exists():
            meta.unlink()
