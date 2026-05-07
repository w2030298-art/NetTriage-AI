"""Step 41: Batch API — CSV upload, status, and download endpoints. [scope:review]"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from starlette.responses import FileResponse

from nettriage.api.dependencies import get_batch_service
from nettriage.api.errors import APIError, APIErrorCode
from nettriage.repositories.batch_repository import BatchNotFoundError
from nettriage.schemas.batch import BatchCreateResponse, BatchStatusResponse
from nettriage.services.batch_service import BatchService

router = APIRouter(prefix="/api/v1", tags=["batches"])


@router.post("/batches", response_model=BatchCreateResponse, status_code=201)
async def create_batch(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    service: BatchService = Depends(get_batch_service),  # noqa: B008
) -> BatchCreateResponse:
    """Upload a CSV file for batch fault classification.

    The batch is queued for background processing. Use the returned
    ``batch_id`` to poll for status and download results.
    """
    return service.create_batch(
        upload_file=file,
        background_tasks=background_tasks,
    )


@router.get("/batches/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    service: BatchService = Depends(get_batch_service),  # noqa: B008
) -> BatchStatusResponse:
    """Query the current status and progress of a batch job."""
    try:
        return service.get_batch_status(batch_id)
    except BatchNotFoundError as exc:
        raise APIError(
            code=APIErrorCode.BATCH_NOT_FOUND,
            message=str(exc),
        ) from exc


@router.get("/batches/{batch_id}/download")
async def download_batch_results(
    batch_id: str,
    service: BatchService = Depends(get_batch_service),  # noqa: B008
) -> FileResponse:
    """Download the result CSV file for a completed batch.

    Uses path-traversal protection via ``ensure_within_directory``.
    """
    try:
        output_path: Path = service.get_batch_download_path(batch_id)
    except BatchNotFoundError as exc:
        raise APIError(
            code=APIErrorCode.BATCH_NOT_FOUND,
            message=str(exc),
        ) from exc
    except ValueError as exc:
        raise APIError(
            code=APIErrorCode.VALIDATION_ERROR,
            message=str(exc),
        ) from exc

    return FileResponse(
        path=str(output_path),
        media_type="text/csv",
        filename=output_path.name,
    )
