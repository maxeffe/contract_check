import pytest
import sys
import os
from decimal import Decimal
from sqlmodel import create_engine, Session, SQLModel
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
import os
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_USER"] = "test"
os.environ["DB_PASS"] = "test"
os.environ["DB_NAME"] = "test"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only"

from api import app
from database.database import get_session

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def sample_user_data():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
        "role": "USER"
    }

@pytest.fixture
def sample_user_data_raw():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
        "role": "USER"
    }

@pytest.fixture
def sample_admin_data():
    return {
        "username": "adminuser",
        "email": "admin@example.com", 
        "password": "admin123",
        "role": "ADMIN"
    }

@pytest.fixture(name="client")
def client_fixture(session):
    """TestClient для API тестов с переопределенной сессией БД"""
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user_credentials():
    return {
        "username": "testuser_api",
        "email": "testapi@example.com",
        "password": "testpassword123"
    }

@pytest.fixture
def admin_user_credentials():
    return {
        "username": "adminuser_api",
        "email": "adminapi@example.com", 
        "password": "adminpassword123"
    }