from __future__ import annotations

import uuid
from collections.abc import Sequence
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.crop import CropImage
from app.repositories.crop_image_repository import CropImageRepository
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    ImagePersistenceError,
    ImageStorageError,
    ImageTooLargeError,
    ImageValidationError,
)
from app.services.farm_service import FarmService
from app.services.timeline_service import TimelineService


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
CHUNK_SIZE_BYTES = 1024 * 1024


class CropImageService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CropImageRepository(db)
        self.farm_service = FarmService(db)
        self.timeline_service = TimelineService(db)
        self.upload_root = self._resolve_upload_root()

    def upload_image(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        image: UploadFile,
    ) -> CropImage:
        self._ensure_farm_owner(user_id, farm_id)

        original_filename = self._clean_original_filename(image.filename)
        extension = self._validate_extension(original_filename)
        content_type = self._validate_content_type(image.content_type)

        farm_upload_dir = self.upload_root / "farms" / str(farm_id)
        stored_filename = f"{uuid.uuid4()}{extension}"
        absolute_file_path = farm_upload_dir / stored_filename
        file_path = self._stored_file_path(absolute_file_path)

        file_size = self._write_image(image, absolute_file_path)

        crop_image = CropImage(
            farm_id=farm_id,
            user_id=user_id,
            file_path=file_path,
            original_filename=original_filename,
            content_type=content_type,
            file_size=file_size,
        )
        self.repository.add(crop_image)

        try:
            self.db.flush()
            self.timeline_service.add_event(
                farm_id=farm_id,
                user_id=user_id,
                event_type="image_upload",
                title="Crop image uploaded",
                description=f"Uploaded {original_filename}",
                source="image_upload",
                payload={
                    "crop_image_id": str(crop_image.id),
                    "original_filename": original_filename,
                    "content_type": content_type,
                    "file_size": file_size,
                    "file_path": file_path,
                },
            )
            self.db.commit()
            self.db.refresh(crop_image)
        except SQLAlchemyError as exc:
            self.db.rollback()
            self._remove_file(absolute_file_path)
            raise ImagePersistenceError from exc

        return crop_image

    def list_images(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[CropImage]:
        self._ensure_farm_owner(user_id, farm_id)

        try:
            return self.repository.list_by_farm(farm_id, skip=skip, limit=limit)
        except SQLAlchemyError as exc:
            raise ImagePersistenceError from exc

    def _ensure_farm_owner(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> None:
        try:
            self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError as exc:
            raise ImagePersistenceError from exc

    def _clean_original_filename(self, filename: str | None) -> str:
        original_filename = Path(filename or "").name.strip()
        if not original_filename:
            raise ImageValidationError(
                "Uploaded image must include an original filename",
            )
        if len(original_filename) > 255:
            raise ImageValidationError(
                "Original filename must be 255 characters or fewer",
            )
        return original_filename

    def _validate_extension(self, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise ImageValidationError(
                "Only jpg, jpeg, png, and webp images are allowed",
            )
        return extension

    def _validate_content_type(self, content_type: str | None) -> str:
        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise ImageValidationError(
                "Only jpg, jpeg, png, and webp images are allowed",
            )
        return content_type

    def _write_image(self, image: UploadFile, destination: Path) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True)
        max_size_bytes = settings.max_image_upload_size_mb * 1024 * 1024
        file_size = 0

        try:
            image.file.seek(0)
            with destination.open("wb") as output_file:
                while True:
                    chunk = image.file.read(CHUNK_SIZE_BYTES)
                    if not chunk:
                        break

                    file_size += len(chunk)
                    if file_size > max_size_bytes:
                        raise ImageTooLargeError(
                            f"Image must be {settings.max_image_upload_size_mb} MB or smaller",
                        )

                    output_file.write(chunk)
        except ImageValidationError:
            self._remove_file(destination)
            raise
        except OSError as exc:
            self._remove_file(destination)
            raise ImageStorageError from exc

        if file_size == 0:
            self._remove_file(destination)
            raise ImageValidationError("Uploaded image cannot be empty")

        return file_size

    def _remove_file(self, file_path: Path) -> None:
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _resolve_upload_root(self) -> Path:
        configured_upload_dir = Path(settings.upload_dir)
        if configured_upload_dir.is_absolute():
            return configured_upload_dir
        return self._backend_root() / configured_upload_dir

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _stored_file_path(self, absolute_file_path: Path) -> str:
        try:
            return str(absolute_file_path.relative_to(self._backend_root()))
        except ValueError:
            return str(absolute_file_path)
