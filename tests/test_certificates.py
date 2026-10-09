import uuid
from pathlib import Path
from unittest.mock import patch
import pytest

from app.config import GENERATED_DIR
from app.models import Job, Certificate, JobStatus, CertificateStatus
from app.services.certificate_service import generate_certificate_pdf, get_certificate_path


def test_generate_certificate_pdf_creates_valid_file(tmp_path):
    cert_id = str(uuid.uuid4())
    output_file = tmp_path / f"cert_{cert_id}.pdf"

    result_path = generate_certificate_pdf(
        certificate_id=cert_id,
        recipient_name="Alice Smith",
        course_name="Machine Learning Bootcamp",
        completion_date="2026-10-09",
        output_path=output_file,
    )

    assert result_path.exists()
    assert result_path.stat().st_size > 0
    with open(result_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


def test_certificate_contains_all_required_elements(tmp_path):
    """
    Verify that the generated PDF contains recipient name, course name,
    completion date, and the unique certificate ID in the output file.
    """
    cert_id = str(uuid.uuid4())
    recipient_name = "Elena Rostova"
    course_name = "Advanced Systems Architecture"
    completion_date = "2026-10-09"

    output_file = tmp_path / f"cert_{cert_id}.pdf"
    result_path = generate_certificate_pdf(
        certificate_id=cert_id,
        recipient_name=recipient_name,
        course_name=course_name,
        completion_date=completion_date,
        output_path=output_file,
    )

    pdf_bytes = result_path.read_bytes()
    # Check PDF header
    assert pdf_bytes.startswith(b"%PDF-")
    # Check required text elements in generated PDF bytes
    assert recipient_name.encode() in pdf_bytes
    assert course_name.encode() in pdf_bytes
    assert completion_date.encode() in pdf_bytes
    assert cert_id.encode() in pdf_bytes


def test_retrieve_unknown_certificate_404(client):
    response = client.get(f"/api/certificates/{uuid.uuid4()}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_retrieve_pending_certificate_409(client, db_session):
    job = Job(id=str(uuid.uuid4()), status=JobStatus.QUEUED.value, total_count=1)
    cert = Certificate(
        id=str(uuid.uuid4()),
        job_id=job.id,
        recipient_name="Pending User",
        recipient_email="pending@example.com",
        course="AI Engineering",
        completion_date="2026-10-09",
        status=CertificateStatus.PENDING.value,
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/certificates/{cert.id}")
    assert response.status_code == 409
    assert "in progress" in response.json()["detail"].lower()


def test_retrieve_failed_certificate_400(client, db_session):
    job = Job(id=str(uuid.uuid4()), status=JobStatus.COMPLETED_WITH_ERRORS.value, total_count=1, failed_count=1)
    cert = Certificate(
        id=str(uuid.uuid4()),
        job_id=job.id,
        recipient_name="Failed User",
        recipient_email="failed@example.com",
        course="Cybersecurity",
        completion_date="2026-10-09",
        status=CertificateStatus.FAILED.value,
        error_message="Canvas rendering error: out of bounds",
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/certificates/{cert.id}")
    assert response.status_code == 400
    assert "Canvas rendering error" in response.json()["detail"]


def test_retrieve_missing_file_on_server_404(client, db_session, tmp_path):
    job = Job(id=str(uuid.uuid4()), status=JobStatus.COMPLETED.value, total_count=1, successful_count=1)
    missing_file = tmp_path / "deleted_cert.pdf"
    cert = Certificate(
        id=str(uuid.uuid4()),
        job_id=job.id,
        recipient_name="Ghost User",
        recipient_email="ghost@example.com",
        course="DevOps",
        completion_date="2026-10-09",
        status=CertificateStatus.SUCCESS.value,
        file_path=str(missing_file),
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/certificates/{cert.id}")
    assert response.status_code == 404
    assert "missing on server" in response.json()["detail"].lower()


def test_retrieve_path_traversal_blocked_403(client, db_session, tmp_path):
    # If a certificate's file_path is somehow set to a file outside GENERATED_DIR, access must be denied
    outside_file = tmp_path.parent / "secret.txt"
    outside_file.write_text("sensitive data")

    job = Job(id=str(uuid.uuid4()), status=JobStatus.COMPLETED.value, total_count=1, successful_count=1)
    cert = Certificate(
        id=str(uuid.uuid4()),
        job_id=job.id,
        recipient_name="Hacker User",
        recipient_email="hacker@example.com",
        course="Penetration Testing",
        completion_date="2026-10-09",
        status=CertificateStatus.SUCCESS.value,
        file_path=str(outside_file),
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/certificates/{cert.id}")
    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


def test_partial_failure_handling(client):
    """
    Simulate scenario where one certificate fails while others succeed.
    Verifies that the entire bulk job does not crash and marks the job COMPLETED_WITH_ERRORS.
    """
    real_generate = generate_certificate_pdf

    def faulty_generate(certificate_id, recipient_name, course_name, completion_date, output_path=None):
        if "Bad User" in recipient_name:
            raise RuntimeError("Simulated PDF font rendering crash")
        return real_generate(certificate_id, recipient_name, course_name, completion_date, output_path)

    with patch("app.services.job_service.generate_certificate_pdf", side_effect=faulty_generate):
        payload = {
            "recipients": [
                {
                    "name": "Bad User",
                    "email": "bad@example.com",
                    "course": "Distributed Systems",
                    "date": "2026-10-09",
                },
                {
                    "name": "Good User",
                    "email": "good@example.com",
                    "course": "Distributed Systems",
                    "date": "2026-10-09",
                },
            ]
        }
        post_res = client.post("/api/jobs", json=payload)
        assert post_res.status_code == 202
        job_id = post_res.json()["job_id"]

        get_res = client.get(f"/api/jobs/{job_id}")
        assert get_res.status_code == 200
        data = get_res.json()

        assert data["status"] == "COMPLETED_WITH_ERRORS"
        assert data["total"] == 2
        assert data["successful"] == 1
        assert data["failed"] == 1
        assert data["progress"] == 100.0

        certs = {c["recipient_name"]: c for c in data["certificates"]}
        
        # Verify Bad User failed gracefully
        bad_cert = certs["Bad User"]
        assert bad_cert["status"] == "FAILED"
        assert "Simulated PDF font rendering crash" in bad_cert["error"]

        # Verify Good User succeeded
        good_cert = certs["Good User"]
        assert good_cert["status"] == "SUCCESS"
        assert good_cert["error"] is None

        # Test downloading Good User's certificate
        good_download = client.get(f"/api/certificates/{good_cert['certificate_id']}")
        assert good_download.status_code == 200
        assert good_download.headers["content-type"] == "application/pdf"
        assert good_download.content.startswith(b"%PDF-")

        # Test downloading Bad User's certificate gives 400
        bad_download = client.get(f"/api/certificates/{bad_cert['certificate_id']}")
        assert bad_download.status_code == 400
        assert "Simulated PDF font rendering crash" in bad_download.json()["detail"]


def test_continuation_after_individual_failure(client):
    """
    Test 3 recipients where the FIRST recipient fails.
    Explicitly verifies that the 2nd and 3rd recipients continued generating successfully.
    """
    real_generate = generate_certificate_pdf

    def fail_first_recipient(certificate_id, recipient_name, course_name, completion_date, output_path=None):
        if "First User Fails" in recipient_name:
            raise RuntimeError("First recipient failed to render")
        return real_generate(certificate_id, recipient_name, course_name, completion_date, output_path)

    with patch("app.services.job_service.generate_certificate_pdf", side_effect=fail_first_recipient):
        payload = {
            "recipients": [
                {
                    "name": "First User Fails",
                    "email": "first@example.com",
                    "course": "Data Pipelines",
                    "date": "2026-10-09",
                },
                {
                    "name": "Second User Succeeds",
                    "email": "second@example.com",
                    "course": "Data Pipelines",
                    "date": "2026-10-09",
                },
                {
                    "name": "Third User Succeeds",
                    "email": "third@example.com",
                    "course": "Data Pipelines",
                    "date": "2026-10-09",
                },
            ]
        }
        res = client.post("/api/jobs", json=payload)
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        status_res = client.get(f"/api/jobs/{job_id}")
        assert status_res.status_code == 200
        data = status_res.json()

        assert data["status"] == "COMPLETED_WITH_ERRORS"
        assert data["total"] == 3
        assert data["successful"] == 2
        assert data["failed"] == 1
        assert data["progress"] == 100.0

        certs = {c["recipient_name"]: c for c in data["certificates"]}
        assert certs["First User Fails"]["status"] == "FAILED"
        assert certs["Second User Succeeds"]["status"] == "SUCCESS"
        assert certs["Third User Succeeds"]["status"] == "SUCCESS"


def test_all_certificates_failed_behavior(client):
    """
    Test scenario where EVERY certificate fails generation.
    Verifies that the job terminates with status FAILED, successful=0, failed=total.
    """
    with patch("app.services.job_service.generate_certificate_pdf", side_effect=RuntimeError("Global rendering fault")):
        payload = {
            "recipients": [
                {
                    "name": "Fail One",
                    "email": "one@example.com",
                    "course": "Algorithms",
                    "date": "2026-10-09",
                },
                {
                    "name": "Fail Two",
                    "email": "two@example.com",
                    "course": "Algorithms",
                    "date": "2026-10-09",
                },
            ]
        }
        res = client.post("/api/jobs", json=payload)
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        status_res = client.get(f"/api/jobs/{job_id}")
        assert status_res.status_code == 200
        data = status_res.json()

        assert data["status"] == "FAILED"
        assert data["total"] == 2
        assert data["successful"] == 0
        assert data["failed"] == 2
        assert data["progress"] == 100.0
        for c in data["certificates"]:
            assert c["status"] == "FAILED"
            assert "Global rendering fault" in c["error"]


def test_full_integration_flow(client):
    """
    End-to-end integration test:
    POST job -> background processing -> certificate generation -> job status -> certificate retrieval
    """
    payload = {
        "recipients": [
            {
                "name": "Devin Torres",
                "email": "devin@example.com",
                "course": "Full-Stack Web Architecture",
                "date": "2026-10-09",
            },
            {
                "name": "Sarah Connor",
                "email": "sarah@example.com",
                "course": "Full-Stack Web Architecture",
                "date": "2026-10-09",
            },
        ]
    }

    # Step 1: POST Job
    post_res = client.post("/api/jobs", json=payload)
    assert post_res.status_code == 202
    job_id = post_res.json()["job_id"]
    assert job_id is not None

    # Step 2: GET Job Status
    status_res = client.get(f"/api/jobs/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()

    assert status_data["status"] == "COMPLETED"
    assert status_data["total"] == 2
    assert status_data["successful"] == 2
    assert status_data["failed"] == 0
    assert status_data["progress"] == 100.0
    assert len(status_data["certificates"]) == 2

    # Step 3: Retrieve Certificate for each recipient
    for cert in status_data["certificates"]:
        cert_id = cert["certificate_id"]
        download_res = client.get(f"/api/certificates/{cert_id}")
        assert download_res.status_code == 200
        assert download_res.headers["content-type"] == "application/pdf"
        assert download_res.content.startswith(b"%PDF-")


def test_multiple_certificate_failures_in_mixed_batch(client):
    """
    Test a 5-recipient batch where MULTIPLE certificates fail (2 fail, 3 succeed).
    Verifies that counters, statuses, and retrievability match expectations.
    """
    real_generate = generate_certificate_pdf

    def selective_failures(certificate_id, recipient_name, course_name, completion_date, output_path=None):
        if "FailMe" in recipient_name:
            raise RuntimeError(f"Rendering failed for {recipient_name}")
        return real_generate(certificate_id, recipient_name, course_name, completion_date, output_path)

    with patch("app.services.job_service.generate_certificate_pdf", side_effect=selective_failures):
        payload = {
            "recipients": [
                {"name": "Pass One", "email": "p1@example.com", "course": "Physics", "date": "2026-10-09"},
                {"name": "FailMe Alpha", "email": "f1@example.com", "course": "Physics", "date": "2026-10-09"},
                {"name": "Pass Two", "email": "p2@example.com", "course": "Physics", "date": "2026-10-09"},
                {"name": "FailMe Beta", "email": "f2@example.com", "course": "Physics", "date": "2026-10-09"},
                {"name": "Pass Three", "email": "p3@example.com", "course": "Physics", "date": "2026-10-09"},
            ]
        }
        res = client.post("/api/jobs", json=payload)
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        status_res = client.get(f"/api/jobs/{job_id}")
        assert status_res.status_code == 200
        data = status_res.json()

        assert data["status"] == "COMPLETED_WITH_ERRORS"
        assert data["total"] == 5
        assert data["successful"] == 3
        assert data["failed"] == 2
        assert data["progress"] == 100.0

        certs_by_name = {c["recipient_name"]: c for c in data["certificates"]}
        # Verify both failed certificates have error messages
        assert "Rendering failed for FailMe Alpha" in certs_by_name["FailMe Alpha"]["error"]
        assert "Rendering failed for FailMe Beta" in certs_by_name["FailMe Beta"]["error"]
        assert certs_by_name["FailMe Alpha"]["status"] == "FAILED"
        assert certs_by_name["FailMe Beta"]["status"] == "FAILED"

        # Verify downloading failed returns 400
        assert client.get(f"/api/certificates/{certs_by_name['FailMe Alpha']['certificate_id']}").status_code == 400

        # Verify all 3 successful certificates return 200 with valid PDF
        for pass_name in ["Pass One", "Pass Two", "Pass Three"]:
            assert certs_by_name[pass_name]["status"] == "SUCCESS"
            cert_download = client.get(f"/api/certificates/{certs_by_name[pass_name]['certificate_id']}")
            assert cert_download.status_code == 200
            assert cert_download.content.startswith(b"%PDF-")


def test_recipient_specific_information_isolation(client):
    """
    Verify that in a batch with multiple recipients, each generated certificate
    exclusively contains the data for its corresponding recipient and not others.
    """
    payload = {
        "recipients": [
            {
                "name": "Maya Lin",
                "email": "maya@example.com",
                "course": "Architecture Design",
                "date": "2026-10-09",
            },
            {
                "name": "Carlos Silva",
                "email": "carlos@example.com",
                "course": "Robotics Engineering",
                "date": "2026-10-09",
            },
        ]
    }
    res = client.post("/api/jobs", json=payload)
    job_id = res.json()["job_id"]

    status_data = client.get(f"/api/jobs/{job_id}").json()
    certs = {c["recipient_name"]: c for c in status_data["certificates"]}

    # Download Maya's certificate
    maya_pdf = client.get(f"/api/certificates/{certs['Maya Lin']['certificate_id']}").content
    # Download Carlos's certificate
    carlos_pdf = client.get(f"/api/certificates/{certs['Carlos Silva']['certificate_id']}").content

    # Maya's PDF must contain Maya's details and NOT Carlos's
    assert b"Maya Lin" in maya_pdf
    assert b"Architecture Design" in maya_pdf
    assert certs["Maya Lin"]["certificate_id"].encode() in maya_pdf
    assert b"Carlos Silva" not in maya_pdf
    assert b"Robotics Engineering" not in maya_pdf

    # Carlos's PDF must contain Carlos's details and NOT Maya's
    assert b"Carlos Silva" in carlos_pdf
    assert b"Robotics Engineering" in carlos_pdf
    assert certs["Carlos Silva"]["certificate_id"].encode() in carlos_pdf
    assert b"Maya Lin" not in carlos_pdf
    assert b"Architecture Design" not in carlos_pdf


def test_progress_bounds_and_edge_cases():
    """Verify progress calculation edge cases never return negative or >100 values."""
    job = Job(id="edge-case-job", total_count=10, successful_count=0, failed_count=0)
    assert job.calculate_progress() == 0.0

    # Negative processed bounds check
    job.successful_count = -5
    assert job.calculate_progress() == 0.0

    # Overflow bounds check
    job.successful_count = 15
    assert job.calculate_progress() == 100.0

    # Zero total count
    job.total_count = 0
    assert job.calculate_progress() == 0.0

