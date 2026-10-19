import pytest

# The database URL must be redirected before app.config is imported, otherwise
# the engine binds to the real job_hunter.db. Tests that write to the live
# database leave junk rows ("Dev", "Job at example.com") in the user's real data.
TEST_DB_URL = "sqlite:///./test_job_hunter.db"

import os

os.environ["DATABASE_URL"] = TEST_DB_URL

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_database():
    """Give every test a clean schema in the throwaway database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client