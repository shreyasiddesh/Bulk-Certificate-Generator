import uuid
from unittest.mock import patch
import pytest
from app.models import Job, Certificate, JobStatus, CertificateStatus
from app.services.job_service import process_job


def test_create_job_success(client):
    payload = {
        "recipients": [
            {
                "name": "Rahul Sharma",
                "email": "rahul@example.com",
                "course": "Python Programming",
                "date": "2026-10-09",
            },
            {
                "name": "Ananya Rao",
                "email": "ananya@example.com",
                "course": "Data Science",
                "date": "2026-10-09",
            },
        ]
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["total"] == 2
    assert data["status"] in ["QUEUED", "PROCESSING", "COMPLETED"]


def test_create_job_empty_recipients_validation(client):
    payload = {"recipients": []}
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "errors" in data


def test_create_job_invalid_email_validation(client):
    payload = {
        "recipients": [
            {
                "name": "Invalid Email User",
                "email": "not-an-email",
                "course": "Python Programming",
                "date": "2026-10-09",
            }
        ]
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("email" in err["field"] for err in data["errors"])


def test_create_job_empty_name_validation(client):
    payload = {
        "recipients": [
            {
                "name": "   ",
                "email": "user@example.com",
                "course": "Python Programming",
                "date": "2026-10-09",
            }
        ]
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("name" in err["field"] for err in data["errors"])


def test_create_job_invalid_date_validation(client):
    payload = {
        "recipients": [
            {
                "name": "Valid Name",
                "email": "user@example.com",
                "course": "Python Programming",
                "date": "2026-13-45",  # Invalid month/day
            }
        ]
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("date" in err["field"] for err in data["errors"])


def test_create_job_missing_fields_validation(client):
    # Missing course and date
    payload = {
        "recipients": [
            {
                "name": "Incomplete User",
                "email": "incomplete@example.com",
            }
        ]
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert len(data["errors"]) >= 2


def test_create_job_malformed_json_validation(client):
    # Completely broken JSON payload
    response = client.post(
        "/api/jobs",
        content="{\"recipients\": [unclosed_json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_create_job_invalid_request_types(client):
    # Recipients is a string instead of a list
    payload = {"recipients": "not-a-list"}
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422


def test_create_job_duplicate_emails_allowed(client):
    # Multiple recipients with the same email address must be supported without failure
    payload = {
        "recipients": [
            {
                "name": "Rahul Sharma - Module 1",
                "email": "rahul.shared@example.com",
                "course": "Python Beginner",
                "date": "2026-10-09",
            },
            {
                "name": "Rahul Sharma - Module 2",
                "email": "rahul.shared@example.com",
                "course": "Python Advanced",
                "date": "2026-10-09",
            },
        ]
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Verify both were processed successfully
    status_res = client.get(f"/api/jobs/{job_id}")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["status"] == "COMPLETED"
    assert data["successful"] == 2
    assert len(data["certificates"]) == 2


def test_job_zero_progress_before_processing(db_session):
    # Verify that a newly queued job with 0 processed certs does NOT show 100% progress
    job = Job(id=str(uuid.uuid4()), status=JobStatus.QUEUED.value, total_count=5, successful_count=0, failed_count=0)
    db_session.add(job)
    db_session.commit()

    assert job.calculate_progress() == 0.0


def test_get_job_unknown_returns_404(client):
    response = client.get("/api/jobs/nonexistent-uuid-12345")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_job_status_and_progress(client):
    payload = {
        "recipients": [
            {
                "name": "Priya Nair",
                "email": "priya@example.com",
                "course": "Cloud Architecture",
                "date": "2026-10-09",
            }
        ]
    }
    post_res = client.post("/api/jobs", json=payload)
    job_id = post_res.json()["job_id"]

    get_res = client.get(f"/api/jobs/{job_id}")
    assert get_res.status_code == 200
    status_data = get_res.json()

    assert status_data["job_id"] == job_id
    assert status_data["total"] == 1
    assert status_data["successful"] == 1
    assert status_data["failed"] == 0
    assert status_data["progress"] == 100.0
    assert status_data["status"] == "COMPLETED"
    assert len(status_data["certificates"]) == 1
    assert status_data["certificates"][0]["recipient_name"] == "Priya Nair"
    assert status_data["certificates"][0]["status"] == "SUCCESS"


def test_list_recent_jobs(client):
    client.post(
        "/api/jobs",
        json={
            "recipients": [
                {
                    "name": "User One",
                    "email": "one@example.com",
                    "course": "Course A",
                    "date": "2026-10-09",
                }
            ]
        },
    )
    client.post(
        "/api/jobs",
        json={
            "recipients": [
                {
                    "name": "User Two",
                    "email": "two@example.com",
                    "course": "Course B",
                    "date": "2026-10-09",
                }
            ]
        },
    )

    response = client.get("/api/jobs?limit=10")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 2
    assert "job_id" in jobs[0]
    assert "progress" in jobs[0]


def test_unexpected_fatal_job_level_error(client, db_session):
    # Test that an unexpected fatal failure during background job processing
    # marks the job FAILED without leaving it permanently in PROCESSING
    job = Job(id=str(uuid.uuid4()), status=JobStatus.QUEUED.value, total_count=2)
    cert = Certificate(
        id=str(uuid.uuid4()),
        job_id=job.id,
        recipient_name="Test Person",
        recipient_email="test@example.com",
        course="Systems",
        completion_date="2026-10-09",
        status=CertificateStatus.PENDING.value,
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    # Simulate unexpected failure during certificate querying in worker
    with patch("sqlalchemy.orm.Query.order_by", side_effect=RuntimeError("Unexpected DB crash")):
        process_job(job.id)

    db_session.refresh(job)
    assert job.status == JobStatus.FAILED.value
    assert job.completed_at is not None
