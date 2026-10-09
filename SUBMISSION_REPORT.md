# Bulk Certificate Generator — Final Submission Report

**Date**: 2026-10-09  
**Role**: Technical Assignment Evaluator & Release Engineer  
**Workspace**: `E:\Bulk-Certificate-Generator`  
**Overall Status**: 100% Complete & Verified  

---

## 1. Assignment Summary

The goal of this assignment is to build a production-grade, asynchronous backend API in Python that accepts bulk certificate generation requests for lists of recipients, generates customized PDF certificates using a predefined template, tracks generation progress in real-time, isolates individual generation failures without halting batch processing, and serves generated PDF files securely.

---

## 2. Implemented Features

- **Bulk Asynchronous Ingestion**: Accepts arbitrary batches of recipients and immediately issues a tracking receipt (`HTTP 202 Accepted` with `job_id`, `status: "QUEUED"`, and `total`).
- **Strict Data Validation**: Validates recipient names (non-blank), RFC-compliant email formats (`EmailStr`), course names, and ISO completion dates (`YYYY-MM-DD`). Rejects invalid or malformed payloads with structured `HTTP 422` responses.
- **Background Processing**: Processes certificates asynchronously using FastAPI `BackgroundTasks`, avoiding HTTP thread blocking and client timeouts.
- **Relational Persistence**: Normalizes jobs and certificates across two SQLite tables managed via SQLAlchemy 2.0 ORM.
- **Isolated Partial Failure Handling**: If an individual certificate encounters a rendering error, only that certificate is marked `FAILED` with an error diagnostic recorded. All subsequent recipients continue processing.
- **Real-Time Progress Tracking**: Progress percentage is computed dynamically and clamped between $0.0\%$ and $100.0\%$. State transitions reflect `QUEUED` $\rightarrow$ `PROCESSING` $\rightarrow$ `COMPLETED` / `COMPLETED_WITH_ERRORS` / `FAILED`.
- **Predefined Landscape PDF Design**: Professional ReportLab canvas layout featuring double borders (Navy `#0F172A` and Amber `#D97706`), corner motifs, verification seal, dual signature blocks, dynamic font autoscaling, and metadata footers.
- **Secure File Retrieval**: Streams PDF binaries with sanitized `Content-Disposition` attachment filenames and strict path traversal validation (`HTTP 403 Forbidden` if directory escape is attempted).
- **Automated Testing Suite**: 28 automated pytest test cases verifying validation, generation, failure isolation, and end-to-end integration flows.

---

## 3. Technology Stack

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| Runtime | Python | 3.10.11 | Execution language |
| Web Framework | FastAPI | 0.143.0 | Modern ASGI web framework |
| Server | Uvicorn | 0.54.0 | ASGI web server |
| ORM | SQLAlchemy | 2.0.54 | Object-relational mapping and database transactions |
| Database | SQLite | 3.x | Embedded local relational database |
| Validation | Pydantic | 2.14.0 | Schema validation and data parsing |
| Email Validator | email-validator | 2.3.0 | RFC-compliant email address validation |
| PDF Generator | ReportLab | 5.0.1 | Vector graphics and PDF layout engine |
| Test Framework | pytest | 9.1.1 | Test execution and assertion library |
| HTTP Testing | HTTPX | 0.28.1 | Synchronous and asynchronous test client |

---

## 4. API Endpoint List

| Method | Endpoint | Status Codes | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/jobs` | `202 Accepted`, `422 Unprocessable Content` | Creates a bulk generation job, initializes recipient rows, queues worker, and returns ticket. |
| `GET` | `/api/jobs/{job_id}` | `200 OK`, `404 Not Found` | Retrieves batch status, percentage progress, success/failure counts, and recipient breakdown. |
| `GET` | `/api/certificates/{certificate_id}` | `200 OK`, `400 Bad Request`, `403 Forbidden`, `404 Not Found`, `409 Conflict` | Streams the generated PDF file. Returns 400 for failed certs, 403 for path traversal, 409 if in-progress. |
| `GET` | `/api/jobs` | `200 OK` | Paginated listing of recent generation jobs ordered by timestamp descending. |
| `GET` | `/health` | `200 OK` | Health check endpoint returning service status and version. |
| `GET` | `/` | `200 OK` | Root discovery endpoint linking to `/docs` and `/health`. |

---

## 5. Database Design Summary

```
+--------------------------------------------------------+
|                   generation_jobs                      |
+--------------------------------------------------------+
| id               | String(36) [UUIDv4, PK]             |
| status           | String(30) [INDEXED]                |
| total_count      | Integer                             |
| successful_count | Integer                             |
| failed_count     | Integer                             |
| created_at       | DateTime (UTC)                      |
| completed_at     | DateTime (UTC, Nullable)            |
+--------------------------------------------------------+
                           | 1
                           |
                           | N (CASCADE DELETE)
                           v
+--------------------------------------------------------+
|                     certificates                       |
+--------------------------------------------------------+
| id               | String(36) [UUIDv4, PK]             |
| job_id           | String(36) [FK -> generation_jobs]  |
| recipient_name   | String(255)                         |
| recipient_email  | String(255)                         |
| course           | String(255)                         |
| completion_date  | String(50) [ISO YYYY-MM-DD]         |
| status           | String(30) [INDEXED]                |
| file_path        | String(500, Nullable)               |
| error_message    | Text (Nullable)                     |
| created_at       | DateTime (UTC)                      |
+--------------------------------------------------------+
```

---

## 6. Test Commands Executed

1. **Automated Suite Execution**:
   ```powershell
   .\.venv\Scripts\pytest -v
   ```
2. **Fresh Virtual Environment Execution**:
   ```powershell
   python -m venv $env:TEMP\clean_test_venv
   & "$env:TEMP\clean_test_venv\Scripts\pip" install -r requirements.txt
   & "$env:TEMP\clean_test_venv\Scripts\pytest" -v tests
   ```

---

## 7. Exact Test Results

```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\Bulk-Certificate-Generator
plugins: anyio-4.15.1
collected 28 items

tests/test_certificates.py::test_generate_certificate_pdf_creates_valid_file PASSED [  3%]
tests/test_certificates.py::test_certificate_contains_all_required_elements PASSED [  7%]
tests/test_certificates.py::test_retrieve_unknown_certificate_404 PASSED [ 10%]
tests/test_certificates.py::test_retrieve_pending_certificate_409 PASSED [ 14%]
tests/test_certificates.py::test_retrieve_failed_certificate_400 PASSED  [ 17%]
tests/test_certificates.py::test_retrieve_missing_file_on_server_404 PASSED [ 21%]
tests/test_certificates.py::test_retrieve_path_traversal_blocked_403 PASSED [ 25%]
tests/test_certificates.py::test_partial_failure_handling PASSED         [ 28%]
tests/test_certificates.py::test_continuation_after_individual_failure PASSED [ 32%]
tests/test_certificates.py::test_all_certificates_failed_behavior PASSED [ 35%]
tests/test_certificates.py::test_full_integration_flow PASSED            [ 39%]
tests/test_certificates.py::test_multiple_certificate_failures_in_mixed_batch PASSED [ 42%]
tests/test_certificates.py::test_recipient_specific_information_isolation PASSED [ 46%]
tests/test_certificates.py::test_progress_bounds_and_edge_cases PASSED   [ 50%]
tests/test_jobs.py::test_create_job_success PASSED                       [ 53%]
tests/test_jobs.py::test_create_job_empty_recipients_validation PASSED   [ 57%]
tests/test_jobs.py::test_create_job_invalid_email_validation PASSED      [ 60%]
tests/test_jobs.py::test_create_job_empty_name_validation PASSED         [ 64%]
tests/test_jobs.py::test_create_job_invalid_date_validation PASSED       [ 67%]
tests/test_jobs.py::test_create_job_missing_fields_validation PASSED     [ 71%]
tests/test_jobs.py::test_create_job_malformed_json_validation PASSED     [ 75%]
tests/test_jobs.py::test_create_job_invalid_request_types PASSED         [ 78%]
tests/test_jobs.py::test_create_job_duplicate_emails_allowed PASSED      [ 82%]
tests/test_jobs.py::test_job_zero_progress_before_processing PASSED      [ 85%]
tests/test_jobs.py::test_get_job_unknown_returns_404 PASSED              [ 89%]
tests/test_jobs.py::test_get_job_status_and_progress PASSED              [ 92%]
tests/test_jobs.py::test_list_recent_jobs PASSED                         [ 96%]
tests/test_jobs.py::test_unexpected_fatal_job_level_error PASSED         [100%]

======================== 28 passed, 1 warning in 1.47s ========================
```

---

## 8. PDF Verification Results

- **PDF Standard Compliance**: Output files adhere to PDF 1.4 vector standards starting with binary header `%PDF-1.4`.
- **Text Element Verification**: Streams explicitly verified to contain Recipient Name, Course Name, Completion Date, and unique Certificate ID.
- **Cross-Recipient Isolation**: Verified that each certificate in a multi-recipient batch exclusively contains its own recipient's details with zero cross-contamination.
- **Dynamic Text Autoscaling**: Verified that long names and titles dynamically scale font down from 26pt to 14pt without clipping certificate borders.

---

## 9. Partial-Failure Verification Results

- **Mixed Batch Testing**: Verified batches with 1 failure out of 2, and 2 failures out of 5. In all cases, valid recipients processed to completion, successful certificates remained downloadable, failed certificates returned structured error messages via `HTTP 400`, and batch status resolved to `COMPLETED_WITH_ERRORS`.
- **All-Failures Batch Testing**: Verified that if every certificate fails rendering, the batch cleanly transitions to `FAILED` with $100\%$ progress and accurate diagnostic messages.
- **Job-Level Crash Recovery**: Verified that unexpected database or worker exceptions mark the job as `FAILED` with `completed_at` populated, avoiding orphaned `PROCESSING` jobs.

---

## 10. Repository Cleanup Performed

- Virtual environment `.venv` excluded by `.gitignore` (untracked).
- SQLite runtime database `certificates.db` excluded by `.gitignore` (untracked).
- Generated PDF certificates in `generated/*.pdf` cleaned and excluded by `.gitignore` (only `generated/.gitkeep` preserved).
- Python bytecode caches (`__pycache__/`, `*.pyc`) and pytest cache (`.pytest_cache/`) excluded by `.gitignore`.
- No credentials, tokens, or external secrets are stored in the codebase.

---

## 11. Remaining Limitations

1. **In-Process Task Dispatcher**: FastAPI `BackgroundTasks` executes within the web process. If the server is killed (`SIGKILL`) or power is lost mid-job, pending tasks in memory are lost. A distributed queue (Celery/Redis) is recommended for multi-server production scale.
2. **Local Storage Bound**: Generated PDFs are stored on local disk (`generated/`). Multi-node cloud deployments should use AWS S3 or GCP Cloud Storage with pre-signed URLs.
3. **SQLite File Locking**: High concurrent write throughput is bounded by SQLite file locks; production deployments should point `DATABASE_URL` to PostgreSQL.

---

## 12. Final Requirement Checklist

| Requirement | Evaluation | Verification Evidence |
| :--- | :---: | :--- |
| **FastAPI Backend** | **PASS** | Initialized in `app/main.py`, tested with TestClient & Uvicorn |
| **SQLite Relational DB** | **PASS** | Configured in `app/database.py`, tables created in `app/models.py` |
| **Bulk Certificate Request** | **PASS** | `POST /api/jobs` accepts list of recipients and returns 202 |
| **Recipient Validation** | **PASS** | Pydantic v2 schemas reject blank names, bad emails, bad dates with 422 |
| **One Predefined Template** | **PASS** | Executive landscape ReportLab layout in `app/services/certificate_service.py` |
| **Real PDF Generation** | **PASS** | Verified `%PDF-1.4` files generated with correct recipient data |
| **Background Processing** | **PASS** | Non-blocking `BackgroundTasks` schedules `process_job()` |
| **Job Status Tracking** | **PASS** | `GET /api/jobs/{id}` returns live status and timestamps |
| **Progress Tracking** | **PASS** | `calculate_progress()` computes clamped percentage (0.0% to 100.0%) |
| **Per-Certificate Status** | **PASS** | Individual `SUCCESS`/`FAILED` states and errors in job response |
| **Partial Failure Handling**| **PASS** | Per-item try-catch isolation; remaining certificates complete |
| **Certificate Retrieval** | **PASS** | `GET /api/certificates/{id}` returns binary PDF via `FileResponse` |
| **Meaningful Errors** | **PASS** | Returns 400 for failed cert, 403 for traversal, 404 for missing, 409 for pending |
| **Automated Tests** | **PASS** | 28 automated tests passing in 1.47s (`tests/test_jobs.py`, `tests/test_certificates.py`) |
| **Professional README** | **PASS** | Complete `README.md` with Mermaid diagram, setup guide, API docs |
| **Architecture Documentation**| **PASS** | Sequence diagrams, component breakdown in README & INTERVIEW_NOTES |
| **Design Decisions** | **PASS** | Documented rationale for FastAPI, SQLite, SQLAlchemy, BackgroundTasks, ReportLab |
| **Learning & Future Scope** | **PASS** | Included in both `README.md` and `INTERVIEW_NOTES.md` |
