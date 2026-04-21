from __future__ import annotations

from pathlib import Path

from app.infra.storage.local_backend import LocalFilesystemBackend


async def test_local_storage_backend_crud_and_url(tmp_path: Path) -> None:
    storage = LocalFilesystemBackend(tmp_path / "storage")

    file_ref = await storage.upload("assets/resume/test-asset/resume.txt", b"hello")

    assert file_ref == "assets/resume/test-asset/resume.txt"
    assert await storage.exists(file_ref) is True
    assert await storage.download(file_ref) == b"hello"
    assert await storage.get_url(file_ref) == "storage://assets/resume/test-asset/resume.txt"
    assert await storage.delete(file_ref) is True
    assert await storage.exists(file_ref) is False
    assert await storage.delete(file_ref) is False


async def test_local_storage_backend_creates_directory(tmp_path: Path) -> None:
    storage_dir = tmp_path / "nested" / "storage"
    assert storage_dir.exists() is False

    storage = LocalFilesystemBackend(storage_dir)
    file_ref = await storage.upload("assets/jd/test-asset/jd.txt", b"job-description")

    assert storage_dir.exists() is True
    assert await storage.download(file_ref) == b"job-description"
