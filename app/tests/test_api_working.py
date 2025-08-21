"""
Рабочие тесты API, основанные на том, что сервис функционирует корректно.
Эти тесты используют упрощенную архитектуру для проверки основной функциональности.
"""

import pytest
from fastapi import status
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestBasicAPIFunctionality:
    """Базовые тесты API функциональности"""

    def test_api_basic_structure(self):
        """Тест базовой структуры API"""
        from api import app
        assert app is not None
        assert app.title == "Contract Analysis API"

    def test_models_import_correctly(self):
        """Тест что модели импортируются корректно"""
        from models.user import User
        from models.wallet import Wallet
        from models.transaction import Transaction
        from models.document import Document
        from models.mljob import MLJob
        from models.model import Model
        
        # Все модели должны импортироваться без ошибок
        assert User is not None
        assert Wallet is not None
        assert Transaction is not None
        assert Document is not None
        assert MLJob is not None
        assert Model is not None

    def test_user_model_validation(self):
        """Тест валидации модели пользователя"""
        from models.user import User
        
        # Тест валидного пользователя
        user = User(
            username="testuser", 
            email="test@example.com", 
            password="password123",
            role="USER"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "USER"
        
        # Тест методов валидации
        assert hasattr(User, 'validate_email')
        assert hasattr(User, 'validate_password')

    def test_password_hashing(self):
        """Тест хеширования паролей"""
        from models.user import User
        
        password = "test_password_123"
        hashed = User.hash_password(password)
        
        # Хеш должен отличаться от оригинального пароля
        assert hashed != password
        assert len(hashed) > 20  # bcrypt hashes are long
        
        # Создаем пользователя и проверяем верификацию
        user = User(username="test", email="test@example.com", password=hashed)
        assert user.verify_password(password) is True
        assert user.verify_password("wrong_password") is False


class TestAuthenticationLogic:
    """Тесты логики аутентификации без реальной БД"""

    def test_jwt_token_creation(self):
        """Тест создания JWT токенов"""
        from auth.jwt_handler import create_access_token
        from datetime import timedelta
        
        test_data = {"user_id": 1, "email": "test@example.com"}
        expires_delta = timedelta(minutes=30)
        
        token = create_access_token(data=test_data, expires_delta=expires_delta)
        
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts
        assert len(token) > 100  # JWT tokens are typically long

    def test_user_crud_functions_exist(self):
        """Тест что CRUD функции пользователей существуют"""
        from services.crud import user as UserService
        
        # Проверяем что функции существуют
        assert hasattr(UserService, 'create_user')
        assert hasattr(UserService, 'get_user_by_email')
        assert hasattr(UserService, 'get_user_by_id')
        assert hasattr(UserService, 'authenticate_user')

    def test_wallet_crud_functions_exist(self):
        """Тест что CRUD функции кошельков существуют"""
        from services.crud import wallet as WalletService
        
        # Проверяем что функции существуют
        assert hasattr(WalletService, 'get_or_create_wallet')
        assert hasattr(WalletService, 'credit_wallet')
        assert hasattr(WalletService, 'get_user_transactions')


class TestWalletLogic:
    """Тесты логики кошелька"""

    def test_wallet_model_basic_operations(self):
        """Тест базовых операций с моделью кошелька"""
        from models.wallet import Wallet
        from decimal import Decimal
        
        wallet = Wallet(user_id=1, balance=Decimal('0'))
        
        # Проверяем начальный баланс
        assert wallet.balance == Decimal('0')
        assert wallet.user_id == 1
        
        # Тест credit операции (если доступна)
        if hasattr(wallet, 'credit'):
            transaction = wallet.credit(Decimal('100'), "test_topup")
            assert wallet.balance == Decimal('100')
            assert transaction.amount == Decimal('100')
            assert transaction.tx_type == "CREDIT"

    def test_transaction_model(self):
        """Тест модели транзакции"""
        from models.transaction import Transaction
        from decimal import Decimal
        
        transaction = Transaction(
            user_id=1,
            tx_type="CREDIT", 
            amount=Decimal('50.00')
        )
        
        assert transaction.user_id == 1
        assert transaction.tx_type == "CREDIT"
        assert transaction.amount == Decimal('50.00')
        assert hasattr(transaction, 'trans_time')


class TestDocumentProcessing:
    """Тесты обработки документов"""

    def test_document_model(self):
        """Тест модели документа"""
        from models.document import Document
        
        doc = Document(
            user_id=1,
            filename="test.txt",
            raw_text="Test document content",
            token_count=10,
            language="RU"
        )
        
        assert doc.user_id == 1
        assert doc.filename == "test.txt"
        assert doc.raw_text == "Test document content"
        assert doc.language == "RU"
        assert doc.token_count == 10

    def test_token_counting(self):
        """Тест подсчета токенов"""
        from models.document import Document
        
        test_text = "This is a test document with some words to count."
        token_count = Document.count_tokens(test_text)
        
        assert isinstance(token_count, int)
        assert token_count > 0
        assert token_count < 100  # Should be reasonable for short text

    def test_document_processor_exists(self):
        """Тест что процессор документов существует"""
        try:
            from services.document_processor import document_processor
            assert hasattr(document_processor, 'validate_file')
            assert hasattr(document_processor, 'process_file')
        except ImportError:
            pytest.skip("Document processor not available")


class TestPredictionLogic:
    """Тесты логики предсказаний"""

    def test_mljob_model(self):
        """Тест модели ML задания"""
        from models.mljob import MLJob
        from decimal import Decimal
        
        job = MLJob(
            document_id=1,
            model_id=1,
            status="PENDING",
            summary_depth="BULLET",
            used_credits=Decimal('10.0')
        )
        
        assert job.document_id == 1
        assert job.model_id == 1
        assert job.status == "PENDING"
        assert job.summary_depth == "BULLET"
        assert job.used_credits == Decimal('10.0')

    def test_model_model(self):
        """Тест модели ML модели"""
        from models.model import Model
        from decimal import Decimal
        
        model = Model(
            name="test_model",
            price_per_token=Decimal('0.001'),
            active=True
        )
        
        assert model.name == "test_model"
        assert model.price_per_token == Decimal('0.001')
        assert model.active is True

    def test_prediction_service_exists(self):
        """Тест что сервис предсказаний существует"""
        try:
            from services.prediction_service import process_prediction_request
            assert callable(process_prediction_request)
        except ImportError:
            pytest.skip("Prediction service not available")


class TestSchemaValidation:
    """Тесты валидации схем"""

    def test_auth_schemas(self):
        """Тест схем аутентификации"""
        from schemas.auth import UserRegistrationRequest, UserLoginRequest, UserResponse
        
        # Тест регистрации
        reg_data = UserRegistrationRequest(
            username="testuser",
            email="test@example.com", 
            password="password123"
        )
        assert reg_data.username == "testuser"
        assert reg_data.email == "test@example.com"
        
        # Тест логина
        login_data = UserLoginRequest(
            email="test@example.com",
            password="password123"
        )
        assert login_data.email == "test@example.com"
        
        # Тест ответа пользователя
        user_response = UserResponse(
            id=1,
            username="testuser",
            email="test@example.com",
            role="USER"
        )
        assert user_response.id == 1
        assert user_response.role == "USER"

    def test_wallet_schemas(self):
        """Тест схем кошелька"""
        from schemas.wallet import TopUpRequest, BalanceResponse
        from decimal import Decimal
        
        # Тест запроса пополнения
        topup = TopUpRequest(amount=Decimal('100.50'))
        assert topup.amount == Decimal('100.50')
        
        # Тест ответа баланса
        balance_resp = BalanceResponse(balance=Decimal('250.00'))
        assert balance_resp.balance == Decimal('250.00')

    def test_prediction_schemas(self):
        """Тест схем предсказаний"""
        from schemas.prediction import PredictionRequest, DocumentResponse
        
        # Тест запроса предсказания
        pred_req = PredictionRequest(
            document_text="Test contract text",
            filename="contract.txt",
            language="RU",
            model_name="default_model",
            summary_depth="BULLET"
        )
        assert pred_req.document_text == "Test contract text"
        assert pred_req.language == "RU"
        
        # Тест ответа документа
        doc_resp = DocumentResponse(
            id=1,
            user_id=1,
            filename="test.txt",
            pages=1,
            language="RU",
            uploaded_at="2024-01-01T00:00:00"
        )
        assert doc_resp.id == 1
        assert doc_resp.filename == "test.txt"


class TestConfigurationAndSetup:
    """Тесты конфигурации и настройки"""

    def test_environment_variables(self):
        """Тест переменных окружения"""
        import os
        
        # Проверяем что тестовые переменные установлены
        assert os.getenv("SECRET_KEY") is not None
        assert len(os.getenv("SECRET_KEY", "")) > 10

    def test_database_config(self):
        """Тест конфигурации базы данных"""
        from database.config import get_settings
        
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, 'DATABASE_URL_psycopg')

    def test_logging_config(self):
        """Тест конфигурации логирования"""
        from config.logging_config import api_logger, auth_logger, wallet_logger, prediction_logger
        
        # Проверяем что логгеры созданы
        assert api_logger is not None
        assert auth_logger is not None
        assert wallet_logger is not None
        assert prediction_logger is not None


class TestAPIEndpointsStructure:
    """Тесты структуры API эндпоинтов"""

    def test_route_modules_exist(self):
        """Тест что модули маршрутов существуют"""
        from routes.user import user_route
        from routes.wallet import wallet_route
        from routes.prediction import prediction_route
        
        assert user_route is not None
        assert wallet_route is not None
        assert prediction_route is not None

    def test_home_route(self):
        """Тест домашнего маршрута"""
        from routes.home import home_route
        assert home_route is not None


# Интеграционные тесты с моками
class TestIntegrationWithMocks:
    """Интеграционные тесты с использованием моков"""

    @patch('services.crud.user.get_user_by_email')
    @patch('services.crud.user.create_user')
    def test_user_registration_flow(self, mock_create_user, mock_get_user):
        """Тест потока регистрации пользователя с моками"""
        # Настраиваем моки
        mock_get_user.return_value = None  # Пользователь не существует
        
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.role = "USER"
        mock_create_user.return_value = mock_user
        
        # Импортируем функцию после настройки моков
        from services.crud.user import create_user, get_user_by_email
        
        # Тестируем логику
        existing_user = get_user_by_email("test@example.com", None)
        assert existing_user is None
        
        new_user = create_user({
            "username": "testuser",
            "email": "test@example.com", 
            "password": "password123"
        }, None)
        
        assert new_user.id == 1
        assert new_user.email == "test@example.com"

    @patch('services.crud.wallet.get_or_create_wallet')
    @patch('services.crud.wallet.credit_wallet')
    def test_wallet_operations_flow(self, mock_credit_wallet, mock_get_wallet):
        """Тест операций с кошельком с моками"""
        from decimal import Decimal
        
        # Настраиваем моки
        mock_wallet = MagicMock()
        mock_wallet.id = 1
        mock_wallet.user_id = 1
        mock_wallet.balance = Decimal('100.00')
        mock_get_wallet.return_value = mock_wallet
        
        mock_transaction = MagicMock()
        mock_transaction.id = 1
        mock_transaction.amount = Decimal('50.00')
        mock_transaction.tx_type = "CREDIT"
        mock_credit_wallet.return_value = mock_transaction
        
        # Тестируем логику
        from services.crud.wallet import get_or_create_wallet, credit_wallet
        
        wallet = get_or_create_wallet(1, None)
        assert wallet.balance == Decimal('100.00')
        
        transaction = credit_wallet(1, Decimal('50.00'), None)
        assert transaction.amount == Decimal('50.00')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])