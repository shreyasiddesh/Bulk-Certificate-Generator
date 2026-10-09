import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
import app.database as database_module
import app.services.job_service as job_service_module
import app.services.certificate_service as cert_service_module
import app.config as config_module

# In-memory SQLite with StaticPool enables multi-threaded in-memory testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def TestingSessionLocal(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, tmp_path, test_engine, TestingSessionLocal):
    """
    Automatically set up an isolated test database and temporary generated/ directory.
    Cleans up tables before and after each test.
    """
    # Re-create fresh schema
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Point generated dir to isolated temporary folder
    test_gen_dir = tmp_path / "generated"
    test_gen_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config_module, "GENERATED_DIR", test_gen_dir)

    # Point SessionLocal in database and services to TestingSessionLocal
    monkeypatch.setattr(database_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(job_service_module, "SessionLocal", TestingSessionLocal)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def db_session(TestingSessionLocal):
    """Direct database session fixture for test assertions."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client
