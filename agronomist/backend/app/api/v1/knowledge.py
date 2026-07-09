from __future__ import annotations

import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import get_current_active_user, get_current_admin, get_knowledge_service
from app.core.config import settings
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeBulkIngestResponse,
    KnowledgeDocumentRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.exceptions import (
    KnowledgeEmbeddingError,
    KnowledgeParseError,
    KnowledgePersistenceError,
    KnowledgeValidationError,
)
from app.services.knowledge_service import KnowledgeService
from app.services.storage_service import StorageService


router = APIRouter(tags=["knowledge"])
logger = logging.getLogger(__name__)


@router.post(
    "/admin/knowledge/documents",
    response_model=KnowledgeBulkIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_knowledge_document(
    file: Annotated[UploadFile, File(...)] = None,
    title: Optional[str] = Form(default=None),
    source_uri: Optional[str] = Form(default=None),
    folder_path: Optional[str] = Form(default=None),
    language: str = Form(default="en"),
    metadata_json: str = Form(default="{}"),
    recursive: bool = Form(default=True),
    force_reindex: bool = Form(default=False),
    dry_run: bool = Form(default=False),
    current_user: User = Depends(get_current_admin),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeBulkIngestResponse:
    try:
        metadata = _parse_metadata(metadata_json)
        if folder_path:
            if dry_run:
                result = knowledge_service.dry_run_folder(
                    folder_path=Path(folder_path).expanduser().resolve(),
                    language=language,
                    recursive=recursive,
                    force_reindex=force_reindex,
                )
                return KnowledgeBulkIngestResponse(
                    documents=[],
                    ingested_count=0,
                    skipped_count=result.skipped_count,
                    errors=result.errors,
                    dry_run=True,
                    dry_run_documents=list(result.documents),
                )

            result = knowledge_service.ingest_folder(
                folder_path=Path(folder_path).expanduser().resolve(),
                language=language,
                metadata=metadata,
                user_id=current_user.id,
                recursive=recursive,
                force_reindex=force_reindex,
            )
            return KnowledgeBulkIngestResponse(
                documents=list(result.documents),
                ingested_count=len(result.documents),
                skipped_count=result.skipped_count,
                errors=result.errors,
            )

        if file is None:
            raise KnowledgeValidationError("Provide either file or folder_path")

        upload_path, staged_storage_key = await _store_upload(file, temporary=dry_run)
        if dry_run:
            try:
                dry_run_document = knowledge_service.dry_run_path(
                    path=upload_path,
                    title=title,
                    source_uri=source_uri or file.filename,
                    language=language,
                    force_reindex=force_reindex,
                )
            finally:
                upload_path.unlink(missing_ok=True)
            return KnowledgeBulkIngestResponse(
                documents=[],
                ingested_count=0,
                skipped_count=0,
                errors=[],
                dry_run=True,
                dry_run_documents=[dry_run_document],
            )

        try:
            document = knowledge_service.ingest_path(
                path=upload_path,
                title=title,
                source_uri=source_uri or file.filename,
                language=language,
                metadata=metadata,
                user_id=current_user.id,
                force_reindex=force_reindex,
            )
        finally:
            if staged_storage_key is not None:
                try:
                    StorageService().delete(staged_storage_key)
                except OSError:
                    logger.warning(
                        "Unable to remove staged knowledge upload: %s",
                        staged_storage_key,
                    )
        return KnowledgeBulkIngestResponse(
            documents=[document],
            ingested_count=1,
            skipped_count=0,
            errors=[],
            dry_run=False,
        )
    except HTTPException:
        logger.exception("Knowledge document ingestion request failed")
        raise
    except (KnowledgeValidationError, KnowledgeParseError) as exc:
        logger.exception("Knowledge document ingestion validation failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_exception_detail(
                exc,
                "Knowledge document ingestion validation failed",
            ),
        ) from exc
    except (KnowledgePersistenceError, KnowledgeEmbeddingError) as exc:
        logger.exception("Knowledge document ingestion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_exception_detail(exc, "Knowledge document ingestion failed"),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected knowledge document ingestion failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_exception_detail(
                exc,
                "Unexpected knowledge document ingestion failure",
            ),
        ) from exc


@router.get(
    "/admin/knowledge/documents",
    response_model=list[KnowledgeDocumentRead],
)
def list_knowledge_documents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_admin),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> list[KnowledgeDocumentRead]:
    del current_user
    try:
        return list(knowledge_service.list_documents(skip=skip, limit=limit))
    except KnowledgePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch knowledge documents",
        )


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    search_in: KnowledgeSearchRequest,
    current_user: User = Depends(get_current_active_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeSearchResponse:
    del current_user
    try:
        return knowledge_service.search(
            query=search_in.query,
            limit=search_in.limit,
            language=search_in.language,
            content_type=search_in.content_type,
            use_hybrid=search_in.use_hybrid,
        )
    except KnowledgeEmbeddingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except KnowledgePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to search knowledge base",
        )


async def _store_upload(
    file: UploadFile,
    *,
    temporary: bool = False,
) -> tuple[Path, str | None]:
    suffix = Path(file.filename or "").suffix.lower()
    if temporary:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(await file.read())
            return Path(temporary_file.name), None

    relative_path = f"incoming/{uuid.uuid4()}{suffix}"
    stored_file = StorageService().write_bytes(
        configured_dir=settings.knowledge_storage_dir,
        relative_path=relative_path,
        payload=await file.read(),
    )
    return stored_file.absolute_path, stored_file.storage_key


def _parse_metadata(metadata_json: str) -> dict:
    try:
        metadata = json.loads(metadata_json or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="metadata_json must be valid JSON",
        ) from exc
    if not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="metadata_json must be a JSON object",
        )
    return metadata


def _exception_detail(exc: Exception, fallback: str) -> str:
    message = str(exc).strip()
    if message:
        return message
    return f"{fallback}: {exc.__class__.__name__}"
