import pytest
import sys
import os
from decimal import Decimal
from sqlmodel import create_engine, Session, SQLModel
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment variables BEFORE importing anything
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_USER"] = "test"
os.environ["DB_PASS"] = "test"
os.environ["DB_NAME"] = "test"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only_12345678"
os.environ["HUGGINGFACE_API_TOKEN"] = "test_token"
os.environ["API_ANALITICS"] = "test_analytics"

# Import models to register them with SQLModel
import models.user
import models.wallet
import models.transaction
import models.document
import models.mljob
import models.model
import models.riskclause

from services.crud.user import create_user


@pytest.fixture(scope="function")
def session():
    """Create test database session with SQLite in-memory database"""
    engine = create_engine(
        "sqlite:///:memory:", 
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(session):
    """TestClient для API тестов с переопределенной сессией БД"""
    from api import app
    from database.database import get_session
    
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }


@pytest.fixture
def sample_admin_data():
    return {
        "username": "adminuser",
        "email": "admin@example.com", 
        "password": "admin123"
    }


@pytest.fixture
def test_user(session):
    """Create test user in database"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    user = create_user(user_data, session)
    return user


@pytest.fixture
def admin_user(session):
    """Create admin user in database"""
    user_data = {
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "admin123"
    }
    user = create_user(user_data, session)
    user.role = "ADMIN"
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post("/auth/signin", json={
        "email": test_user.email,
        "password": "password123"
    })
    assert response.status_code == 200, f"Login failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, admin_user):
    """Get authentication headers for admin user"""
    response = client.post("/auth/signin", json={
        "email": admin_user.email,
        "password": "admin123"
    })
    assert response.status_code == 200, f"Admin login failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_document_text():
    """Sample contract text for testing"""
    return """
    ДОГОВОР АРЕНДЫ ПОМЕЩЕНИЯ
    
    1. ПРЕДМЕТ ДОГОВОРА
    Арендодатель предоставляет Арендатору во временное пользование помещение площадью 100 кв.м.
    
    2. АРЕНДНАЯ ПЛАТА
    Размер арендной платы составляет 50 000 рублей в месяц.
    Арендатор обязан производить оплату до 10 числа каждого месяца.
    
    3. ОТВЕТСТВЕННОСТЬ СТОРОН
    В случае просрочки платежа Арендатор обязан уплатить пеню в размере 0,1% за каждый день просрочки.
    """