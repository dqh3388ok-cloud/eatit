from __future__ import annotations

from pathlib import Path, PurePosixPath
from urllib.parse import quote

import anyio

from app.infra.storage.base import StorageInterface


class LocalFilesystemBackend(StorageInterface):
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir

    async def upload(self, key: str, content: bytes) -> str:
        file_ref = self._normalize_file_ref(key)
        target_path = self._resolve_path(file_ref)
        await anyio.to_thread.run_sync(
            lambda: target_path.parent.mkdir(parents=True, exist_ok=True)
        )
        await anyio.to_thread.run_sync(target_path.write_bytes, content)
        return file_ref

    async def download(self, file_ref: str) -> bytes:
        target_path = self._resolve_path(file_ref)
        return await anyio.to_thread.run_sync(target_path.read_bytes)

    async def delete(self, file_ref: str) -> bool:
        target_path = self._resolve_path(file_ref)
        exists = await anyio.to_thread.run_sync(target_path.exists)
        if not exists:
            return False
        await anyio.to_thread.run_sync(target_path.unlink)
        await anyio.to_thread.run_sync(lambda: self._prune_empty_parents(target_path.parent))
        return True

    async def exists(self, file_ref: str) -> bool:
        target_path = self._resolve_path(file_ref)
        return await anyio.to_thread.run_sync(target_path.exists)

    async def get_url(self, file_ref: str) -> str:
        normalized = self._normalize_file_ref(file_ref)
        return f"storage://{quote(normalized, safe='/')}"

    def _resolve_path(self, file_ref: str) -> Path:
        normalized = self._normalize_file_ref(file_ref)
        return self.storage_dir / Path(*PurePosixPath(normalized).parts)

    @staticmethod
    def _normalize_file_ref(file_ref: str) -> str:
        posix_path = PurePosixPath(file_ref)
        if posix_path.is_absolute() or ".." in posix_path.parts:
            raise ValueError("file_ref must be a relative path without traversal.")
        normalized = str(posix_path)
        if normalized in {"", "."}:
            raise ValueError("file_ref must not be empty.")
        return normalized

    def _prune_empty_parents(self, path: Path) -> None:
        current = path
        while current != self.storage_dir and current.is_relative_to(self.storage_dir):
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent
