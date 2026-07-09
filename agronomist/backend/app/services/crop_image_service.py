from __future__ import annotations

import uuid
from collections.abc import Sequence

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
from app.services.storage_service import StorageService
from app.services.timeline_service import TimelineService


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class CropImageService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CropImageRepository(db)
        self.farm_service = FarmService(db)
        self.timeline_service = TimelineService(db)
        self.storage_service = StorageService()

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

        stored_filename = f"{uuid.uuid4()}{extension}"
        relative_path = f"farms/{farm_id}/{stored_filename}"
        storage_key = self.storage_service.build_storage_key(
            configured_dir=settings.upload_dir,
            relative_path=relative_path,
        )
        file_size = self._write_image(
            image=image,
            relative_path=relative_path,
            storage_key=storage_key,
        )

        crop_image = CropImage(
            farm_id=farm_id,
            user_id=user_id,
            file_path=storage_key,
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
                    "file_path": storage_key,
                },
            )
            self.db.commit()
            self.db.refresh(crop_image)
        except SQLAlchemyError as exc:
            self.db.rollback()
            self._remove_file(storage_key)
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
        original_filename = (filename or "").split("/")[-1].split("\\")[-1].strip()
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
        filename_parts = filename.rsplit(".", 1)
        extension = f".{filename_parts[1].lower()}" if len(filename_parts) == 2 else ""
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

    def _write_image(
        self,
        *,
        image: UploadFile,
        relative_path: str,
        storage_key: str,
    ) -> int:
        max_size_bytes = settings.max_image_upload_size_mb * 1024 * 1024

        try:
            stored_file = self.storage_service.write_upload_file(
                configured_dir=settings.upload_dir,
                relative_path=relative_path,
                upload_file=image,
                max_size_bytes=max_size_bytes,
            )
        except ValueError as exc:
            if str(exc) == "file_too_large":
                raise ImageTooLargeError(
                    f"Image must be {settings.max_image_upload_size_mb} MB or smaller",
                ) from exc
            raise
        except OSError as exc:
            raise ImageStorageError from exc

        if stored_file.size == 0:
            self._remove_file(storage_key)
            raise ImageValidationError("Uploaded image cannot be empty")

        return stored_file.size

    def _remove_file(self, storage_key: str) -> None:
        try:
            self.storage_service.delete(storage_key)
        except OSError:
            pass
