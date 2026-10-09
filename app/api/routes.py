import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.models import CertificateStatus
from app.utils.validation import sanitize_filename
from app.schemas import (
    CreateJobRequest,
    CreateJobResponse,
    JobStatusResponse,
    JobSummaryResponse,
    CertificateItemResponse,
)
from app.services.job_service import (
    create_job,
    get_job_by_id,
    list_jobs,
    get_certificate_by_id,
    process_job,
)

router = APIRouter(prefix="/api", tags=["Certificates & Jobs"])


@router.post(
    "/jobs",
    response_model=CreateJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a bulk certificate generation job",
    description="Accepts a list of recipients, creates a background generation job, and queues processing.",
)
def create_generation_job_endpoint(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> CreateJobResponse:
    job = create_job(db=db, request=request)
    # Schedule asynchronous execution via FastAPI BackgroundTasks
    background_tasks.add_task(process_job, job.id)

    return CreateJobResponse(
        job_id=job.id,
        status=job.status,
        total=job.total_count,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get job status and progress",
    description="Retrieve processing status, percentage progress, and recipient-level certificate status.",
)
def get_job_status_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    job = get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )

    certificates_data = [
        CertificateItemResponse(
            certificate_id=cert.id,
            recipient_name=cert.recipient_name,
            status=cert.status,
            error=cert.error_message,
        )
        for cert in job.certificates
    ]

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        total=job.total_count,
        successful=job.successful_count,
        failed=job.failed_count,
        progress=job.calculate_progress(),
        certificates=certificates_data,
    )


@router.get(
    "/certificates/{certificate_id}",
    summary="Retrieve generated certificate PDF",
    description="Download the generated PDF for a successfully completed certificate.",
)
def get_certificate_endpoint(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    cert = get_certificate_by_id(db=db, certificate_id=certificate_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found",
        )

    if cert.status == CertificateStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate generation failed: {cert.error_message or 'Unknown error'}",
        )

    if cert.status == CertificateStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate generation is still queued or in progress",
        )

    # Status is SUCCESS - verify physical file
    if not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate PDF file is missing on server",
        )

    # Path traversal protection: verify file resides within GENERATED_DIR
    cert_path = Path(cert.file_path).resolve()
    gen_dir = config.GENERATED_DIR.resolve()
    try:
        cert_path.relative_to(gen_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Invalid certificate file location",
        )

    safe_name = sanitize_filename(cert.recipient_name.strip().replace(" ", "_"))
    download_filename = f"certificate_{safe_name}_{cert.id[:8]}.pdf"

    return FileResponse(
        path=str(cert_path),
        media_type="application/pdf",
        filename=download_filename,
    )


@router.get(
    "/jobs",
    response_model=list[JobSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List recent generation jobs",
    description="Retrieve a paginated list of recent bulk certificate generation jobs.",
)
def list_jobs_endpoint(
    limit: int = Query(50, ge=1, le=100, description="Max jobs to return"),
    skip: int = Query(0, ge=0, description="Number of jobs to skip"),
    db: Session = Depends(get_db),
) -> list[JobSummaryResponse]:
    jobs = list_jobs(db=db, limit=limit, skip=skip)
    return [
        JobSummaryResponse(
            job_id=j.id,
            status=j.status,
            total=j.total_count,
            successful=j.successful_count,
            failed=j.failed_count,
            progress=j.calculate_progress(),
            created_at=j.created_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]
