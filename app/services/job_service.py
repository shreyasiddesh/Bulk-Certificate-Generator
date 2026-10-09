import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Job, Certificate, JobStatus, CertificateStatus
from app.schemas import CreateJobRequest
from app.services.certificate_service import generate_certificate_pdf

logger = logging.getLogger("bulk_certificate_generator")


def create_job(db: Session, request: CreateJobRequest) -> Job:
    """
    Initialize a new generation job and persist pending certificate records.
    """
    job_id = str(uuid.uuid4())
    total = len(request.recipients)

    job = Job(
        id=job_id,
        status=JobStatus.QUEUED.value,
        total_count=total,
        successful_count=0,
        failed_count=0,
    )
    db.add(job)

    # Pre-populate certificate records in PENDING status
    for item in request.recipients:
        cert = Certificate(
            id=str(uuid.uuid4()),
            job_id=job_id,
            recipient_name=item.name,
            recipient_email=str(item.email),
            course=item.course,
            completion_date=item.date,
            status=CertificateStatus.PENDING.value,
        )
        db.add(cert)

    try:
        db.commit()
        db.refresh(job)
        return job
    except Exception:
        db.rollback()
        raise


def get_job_by_id(db: Session, job_id: str) -> Optional[Job]:
    """Retrieve a single job with its associated certificates."""
    return db.query(Job).filter(Job.id == job_id).first()


def list_jobs(db: Session, limit: int = 50, skip: int = 0) -> list[Job]:
    """List recent generation jobs ordered by creation timestamp descending."""
    return (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_certificate_by_id(db: Session, certificate_id: str) -> Optional[Certificate]:
    """Retrieve a single certificate record by ID."""
    return db.query(Certificate).filter(Certificate.id == certificate_id).first()


def process_job(job_id: str) -> None:
    """
    Background worker function executed via FastAPI BackgroundTasks.
    
    Processes all pending certificates for a given job. If one certificate fails,
    subsequent certificates continue processing safely.
    """
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("Job %s not found for processing", job_id)
            return

        # Mark job as currently processing
        job.status = JobStatus.PROCESSING.value
        db.commit()

        logger.info("Starting processing for job %s with %d recipients", job_id, job.total_count)

        certificates = (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id)
            .order_by(Certificate.created_at.asc())
            .all()
        )

        for cert in certificates:
            try:
                # Generate certificate PDF
                pdf_path = generate_certificate_pdf(
                    certificate_id=cert.id,
                    recipient_name=cert.recipient_name,
                    course_name=cert.course,
                    completion_date=cert.completion_date,
                )

                cert.file_path = str(pdf_path)
                cert.status = CertificateStatus.SUCCESS.value
                cert.error_message = None
                job.successful_count += 1
                logger.info("Generated certificate %s for %s", cert.id, cert.recipient_name)

            except Exception as e:
                # Catch individual certificate generation failures without failing the batch
                logger.warning(
                    "Failed to generate certificate %s for %s: %s",
                    cert.id,
                    cert.recipient_name,
                    str(e),
                )
                cert.status = CertificateStatus.FAILED.value
                cert.error_message = str(e)
                job.failed_count += 1

            # Commit after each certificate to provide real-time progress updates to polling clients
            try:
                db.commit()
            except Exception as commit_err:
                logger.error("Failed to commit progress for certificate %s: %s", cert.id, commit_err)
                db.rollback()

        # Synchronize and ensure counters match individual certificate records
        job.successful_count = (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id, Certificate.status == CertificateStatus.SUCCESS.value)
            .count()
        )
        job.failed_count = (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id, Certificate.status == CertificateStatus.FAILED.value)
            .count()
        )

        # Update final job status
        if job.total_count == 0:
            job.status = JobStatus.FAILED.value
        elif job.failed_count == 0:
            job.status = JobStatus.COMPLETED.value
        elif job.successful_count > 0:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value
        else:
            job.status = JobStatus.FAILED.value

        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "Job %s finished. Status: %s, Success: %d, Failed: %d",
            job_id,
            job.status,
            job.successful_count,
            job.failed_count,
        )

    except Exception as exc:
        logger.exception("Fatal error while processing job %s: %s", job_id, str(exc))
        try:
            db.rollback()
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            logger.exception("Failed to update fatal status for job %s", job_id)
    finally:
        db.close()
