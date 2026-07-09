from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


CHUNK_SIZE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    absolute_path: Path
    size: int


class StorageService:
    def ensure_ready(self) -> dict[str, str]:
        upload_dir = self.resolve_directory(settings.upload_dir)
        knowledge_dir = self.resolve_directory(settings.knowledge_storage_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        return {
            "storage_backend": settings.storage_backend,
            "upload_dir": str(upload_dir),
            "knowledge_storage_dir": str(knowledge_dir),
        }

    def resolve_directory(self, configured_dir: str) -> Path:
        configured = Path(configured_dir)
        if configured.is_absolute():
            return configured
        return self._backend_root() / configured

    def resolve_storage_path(self, storage_key: str) -> Path:
        path = Path(storage_key)
        if path.is_absolute():
            return path
        return self._backend_root() / path

    def build_storage_key(self, *, configured_dir: str, relative_path: str) -> str:
        safe_relative_path = self._sanitize_relative_path(relative_path)
        configured = Path(configured_dir)
        if configured.is_absolute():
            return str(configured / safe_relative_path)
        return str(configured / safe_relative_path)

    def write_upload_file(
        self,
        *,
        configured_dir: str,
        relative_path: str,
        upload_file: UploadFile,
        max_size_bytes: int | None = None,
    ) -> StoredFile:
        storage_key = self.build_storage_key(
            configured_dir=configured_dir,
            relative_path=relative_path,
        )
        destination = self.resolve_storage_path(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        size = 0

        upload_file.file.seek(0)
        try:
            with destination.open("wb") as output_file:
                while True:
                    chunk = upload_file.file.read(CHUNK_SIZE_BYTES)
                    if not chunk:
                        break
                    size += len(chunk)
                    if max_size_bytes is not None and size > max_size_bytes:
                        raise ValueError("file_too_large")
                    output_file.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        return StoredFile(storage_key=storage_key, absolute_path=destination, size=size)

    def write_bytes(
        self,
        *,
        configured_dir: str,
        relative_path: str,
        payload: bytes,
    ) -> StoredFile:
        storage_key = self.build_storage_key(
            configured_dir=configured_dir,
            relative_path=relative_path,
        )
        destination = self.resolve_storage_path(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        return StoredFile(
            storage_key=storage_key,
            absolute_path=destination,
            size=len(payload),
        )

    def copy_file(
        self,
        *,
        source_path: Path,
        configured_dir: str,
        relative_path: str,
    ) -> StoredFile:
        storage_key = self.build_storage_key(
            configured_dir=configured_dir,
            relative_path=relative_path,
        )
        destination = self.resolve_storage_path(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source_path, destination)
        return StoredFile(
            storage_key=storage_key,
            absolute_path=destination,
            size=destination.stat().st_size,
        )

    def read_bytes(self, storage_key: str) -> bytes:
        return self.resolve_storage_path(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        self.resolve_storage_path(storage_key).unlink(missing_ok=True)

    def _sanitize_relative_path(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise ValueError("Storage relative paths must not be absolute")
        if ".." in candidate.parts:
            raise ValueError("Storage relative paths must not escape the storage root")
        return candidate

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]
