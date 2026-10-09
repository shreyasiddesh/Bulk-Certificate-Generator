from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from app.utils.validation import validate_name, validate_course, validate_date_string


class RecipientInput(BaseModel):
    name: str = Field(..., description="Full name of certificate recipient", examples=["Rahul Sharma"])
    email: EmailStr = Field(..., description="Valid email address of recipient", examples=["rahul@example.com"])
    course: str = Field(..., description="Name of the course or event", examples=["Python Programming"])
    date: str = Field(..., description="Completion date in YYYY-MM-DD format", examples=["2026-10-09"])

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("course")
    @classmethod
    def check_course(cls, v: str) -> str:
        return validate_course(v)

    @field_validator("date")
    @classmethod
    def check_date(cls, v: str) -> str:
        return validate_date_string(v)


class CreateJobRequest(BaseModel):
    recipients: list[RecipientInput] = Field(
        ...,
        description="Non-empty list of recipients for bulk certificate generation",
    )

    @field_validator("recipients")
    @classmethod
    def check_recipients_not_empty(cls, v: list[RecipientInput]) -> list[RecipientInput]:
        if not v or len(v) == 0:
            raise ValueError("Recipients list cannot be empty")
        return v


class CreateJobResponse(BaseModel):
    job_id: str
    status: str
    total: int


class CertificateItemResponse(BaseModel):
    certificate_id: str
    recipient_name: str
    status: str
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    total: int
    successful: int
    failed: int
    progress: float
    certificates: list[CertificateItemResponse]

    model_config = ConfigDict(from_attributes=True)


class JobSummaryResponse(BaseModel):
    job_id: str
    status: str
    total: int
    successful: int
    failed: int
    progress: float
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
