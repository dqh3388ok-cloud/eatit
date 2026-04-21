from __future__ import annotations

from abc import ABC, abstractmethod


class StorageInterface(ABC):
    @abstractmethod
    async def upload(self, key: str, content: bytes) -> str:
        """Persist bytes under an opaque file reference and return that reference."""

    @abstractmethod
    async def download(self, file_ref: str) -> bytes:
        """Load bytes for a previously stored opaque file reference."""

    @abstractmethod
    async def delete(self, file_ref: str) -> bool:
        """Delete a stored object if it exists."""

    @abstractmethod
    async def exists(self, file_ref: str) -> bool:
        """Check whether an opaque file reference exists."""

    @abstractmethod
    async def get_url(self, file_ref: str) -> str:
        """Return a backend-specific URL without exposing local storage roots."""
