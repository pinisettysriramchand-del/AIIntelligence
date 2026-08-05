"""Local filesystem implementation of the ObjectStorage port."""

from __future__ import annotations

import logging
from pathlib import Path

import aiofiles
import aiofiles.os

from stratiq.domain.exceptions import StorageError

logger = logging.getLogger(__name__)


class LocalFileStorage:
    """Implements ObjectStorage using the local filesystem.

    The *root_path* mirrors an S3 bucket: keys map to relative paths inside it.
    """

    def __init__(self, root_path: str) -> None:
        self._root = Path(root_path)
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        resolved = (self._root / key).resolve()
        if not str(resolved).startswith(str(self._root.resolve())):
            raise StorageError(f"Path traversal detected for key: {key}")
        return resolved

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with aiofiles.open(path, "wb") as f:
                await f.write(data)
        except OSError as exc:
            raise StorageError(f"Failed to save {key}: {exc}") from exc
        logger.debug("Saved object", extra={"key": key, "bytes": len(data)})
        return str(path)

    async def load(self, key: str) -> bytes:
        path = Path(key) if Path(key).is_absolute() else self._resolve(key)
        try:
            async with aiofiles.open(path, "rb") as f:
                return await f.read()
        except FileNotFoundError as exc:
            raise StorageError(f"Object not found: {key}") from exc
        except OSError as exc:
            raise StorageError(f"Failed to load {key}: {exc}") from exc

    async def delete(self, key: str) -> None:
        path = Path(key) if Path(key).is_absolute() else self._resolve(key)
        try:
            await aiofiles.os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise StorageError(f"Failed to delete {key}: {exc}") from exc

    async def exists(self, key: str) -> bool:
        path = Path(key) if Path(key).is_absolute() else self._resolve(key)
        return path.exists()
