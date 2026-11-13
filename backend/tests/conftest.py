import pytest
from app.config import settings


@pytest.fixture
def configured_api_key():
    original = settings.api_key
    settings.api_key = "test-api-key"
    yield settings.api_key
    settings.api_key = original
