import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Job(Base):
    __tablename__ = "generation_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(30), default=JobStatus.QUEUED.value, nullable=False, index=True)
    total_count = Column(Integer, default=0, nullable=False)
    successful_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    certificates = relationship(
        "Certificate",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="Certificate.created_at",
    )

    def calculate_progress(self) -> float:
        """Calculate percentage completion of certificate generation."""
        if self.total_count <= 0:
            return 0.0
        processed = self.successful_count + self.failed_count
        return max(0.0, min(100.0, round((processed / self.total_count) * 100, 1)))


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(
        String(36),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    course = Column(String(255), nullable=False)
    completion_date = Column(String(50), nullable=False)
    status = Column(
        String(30),
        default=CertificateStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    job = relationship("Job", back_populates="certificates")
