import pytest

# Option 2: Django Client Setup
# If you are using Django:
# 1. Make sure you have `pytest-django` installed (`pip install pytest-django`).
# 2. `pytest-django` usually provides a `client` fixture automatically, so you might
#    not even need to define it here explicitly. Your tests should just work.
#
# If you need a custom Django client or are not using `pytest-django`'s auto-fixture:
from django.test import Client as DjangoClient


@pytest.fixture(scope="session")
def client() -> DjangoClient:
    return DjangoClient()
