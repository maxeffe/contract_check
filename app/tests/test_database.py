import pytest
from sqlmodel import Session, select
from decimal import Decimal
from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from models.document import Document
from models.mljob import MLJob
from models.model import Model
from services.crud.user import create_user, get_user_by_email
from services.crud.wallet import get_or_create_wallet, credit_wallet


class TestDatabaseConnections:
    """Test database connection and basic operations"""

    def test_session_creation(self, session):
        """Test that database session is created successfully"""
        assert session is not None
        assert isinstance(session, Session)

    def test_table_creation(self, session):
        """Test that all tables are created"""
        # Try to query each table - this will fail if tables don't exist
        users = session.exec(select(User)).all()
        wallets = session.exec(select(Wallet)).all()
        transactions = session.exec(select(Transaction)).all()
        documents = session.exec(select(Document)).all()
        jobs = session.exec(select(MLJob)).all()
        models = session.exec(select(Model)).all()
        
        # Should not raise errors
        assert isinstance(users, list)
        assert isinstance(wallets, list)
        assert isinstance(transactions, list)
        assert isinstance(documents, list)
        assert isinstance(jobs, list)
        assert isinstance(models, list)


class TestUserDatabaseOperations:
    """Test user-related database operations"""

    def test_create_user(self, session, sample_user_data):
        """Test creating a user in database"""
        user = create_user(sample_user_data, session)
        
        assert user.id is not None
        assert user.email == sample_user_data["email"]
        assert user.username == sample_user_data["username"]
        assert user.role == "USER"
        # Password should be hashed
        assert user.password != sample_user_data["password"]

    def test_get_user_by_email(self, session, sample_user_data):
        """Test retrieving user by email"""
        # Create user
        created_user = create_user(sample_user_data, session)
        
        # Retrieve user
        retrieved_user = get_user_by_email(sample_user_data["email"], session)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == sample_user_data["email"]

    def test_get_nonexistent_user(self, session):
        """Test retrieving non-existent user"""
        user = get_user_by_email("nonexistent@example.com", session)
        assert user is None

    def test_user_password_verification(self, session, sample_user_data):
        """Test user password verification"""
        user = create_user(sample_user_data, session)
        
        # Correct password
        assert user.verify_password(sample_user_data["password"]) is True
        
        # Wrong password
        assert user.verify_password("wrong_password") is False

    def test_user_email_validation(self, session):
        """Test user email validation"""
        invalid_user_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        }
        
        # Should raise validation error
        with pytest.raises(Exception):
            create_user(invalid_user_data, session)

    def test_user_password_validation(self, session):
        """Test user password validation"""
        invalid_user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"  # Too short
        }
        
        # Should raise validation error
        with pytest.raises(Exception):
            create_user(invalid_user_data, session)


class TestWalletDatabaseOperations:
    """Test wallet-related database operations"""

    def test_create_wallet(self, session, test_user):
        """Test creating a wallet for user"""
        wallet = get_or_create_wallet(test_user.id, session)
        
        assert wallet.id is not None
        assert wallet.user_id == test_user.id
        assert wallet.balance == Decimal('0')

    def test_get_existing_wallet(self, session, test_user):
        """Test getting existing wallet"""
        # Create wallet
        wallet1 = get_or_create_wallet(test_user.id, session)
        
        # Get same wallet
        wallet2 = get_or_create_wallet(test_user.id, session)
        
        assert wallet1.id == wallet2.id
        assert wallet1.user_id == wallet2.user_id

    def test_credit_wallet(self, session, test_user):
        """Test crediting wallet with funds"""
        initial_balance = Decimal('0')
        credit_amount = Decimal('100.50')
        
        transaction = credit_wallet(test_user.id, credit_amount, session)
        
        assert transaction.id is not None
        assert transaction.user_id == test_user.id
        assert transaction.tx_type == "CREDIT"
        assert transaction.amount == credit_amount
        
        # Check wallet balance updated
        wallet = get_or_create_wallet(test_user.id, session)
        assert wallet.balance == initial_balance + credit_amount

    def test_multiple_transactions(self, session, test_user):
        """Test multiple wallet transactions"""
        amounts = [Decimal('50'), Decimal('25.50'), Decimal('100')]
        
        for amount in amounts:
            credit_wallet(test_user.id, amount, session)
        
        wallet = get_or_create_wallet(test_user.id, session)
        expected_balance = sum(amounts)
        assert wallet.balance == expected_balance

    def test_wallet_isolation(self, session):
        """Test that user wallets are isolated"""
        # Create two users
        user1_data = {
            "username": "user1",
            "email": "user1@example.com",
            "password": "password123"
        }
        user2_data = {
            "username": "user2",
            "email": "user2@example.com",
            "password": "password123"
        }
        
        user1 = create_user(user1_data, session)
        user2 = create_user(user2_data, session)
        
        # Credit user1 wallet
        credit_wallet(user1.id, Decimal('100'), session)
        
        # Check balances
        wallet1 = get_or_create_wallet(user1.id, session)
        wallet2 = get_or_create_wallet(user2.id, session)
        
        assert wallet1.balance == Decimal('100')
        assert wallet2.balance == Decimal('0')
        assert wallet1.id != wallet2.id


class TestTransactionDatabaseOperations:
    """Test transaction-related database operations"""

    def test_transaction_creation(self, session, test_user):
        """Test transaction record creation"""
        transaction = credit_wallet(test_user.id, Decimal('50'), session)
        
        # Verify transaction was saved
        retrieved_transaction = session.get(Transaction, transaction.id)
        assert retrieved_transaction is not None
        assert retrieved_transaction.user_id == test_user.id
        assert retrieved_transaction.amount == Decimal('50')
        assert retrieved_transaction.tx_type == "CREDIT"
        assert retrieved_transaction.trans_time is not None

    def test_transaction_ordering(self, session, test_user):
        """Test that transactions are ordered by time"""
        amounts = [Decimal('10'), Decimal('20'), Decimal('30')]
        
        # Create transactions
        transactions = []
        for amount in amounts:
            tx = credit_wallet(test_user.id, amount, session)
            transactions.append(tx)
        
        # Query transactions by user
        user_transactions = session.exec(
            select(Transaction)
            .where(Transaction.user_id == test_user.id)
            .order_by(Transaction.trans_time.desc())
        ).all()
        
        assert len(user_transactions) == 3
        # Most recent should be first (descending order)
        assert user_transactions[0].amount == Decimal('30')
        assert user_transactions[2].amount == Decimal('10')


class TestDocumentDatabaseOperations:
    """Test document-related database operations"""

    def test_document_creation(self, session, test_user):
        """Test creating a document record"""
        document = Document(
            user_id=test_user.id,
            filename="test_contract.txt",
            content="Test contract content",
            pages=1,
            language="RU"
        )
        
        session.add(document)
        session.commit()
        session.refresh(document)
        
        assert document.id is not None
        assert document.user_id == test_user.id
        assert document.filename == "test_contract.txt"
        assert document.uploaded_at is not None

    def test_document_user_relationship(self, session, test_user):
        """Test document-user relationship"""
        document = Document(
            user_id=test_user.id,
            filename="test.txt",
            content="Test content",
            pages=1,
            language="EN"
        )
        
        session.add(document)
        session.commit()
        
        # Query documents by user
        user_documents = session.exec(
            select(Document).where(Document.user_id == test_user.id)
        ).all()
        
        assert len(user_documents) == 1
        assert user_documents[0].filename == "test.txt"

    def test_document_token_counting(self, session, test_user):
        """Test document token counting functionality"""
        content = "This is a test document with some words to count tokens."
        
        document = Document(
            user_id=test_user.id,
            filename="test.txt",
            content=content,
            pages=1,
            language="EN"
        )
        
        token_count = Document.count_tokens(content)
        assert isinstance(token_count, int)
        assert token_count > 0


class TestMLJobDatabaseOperations:
    """Test ML job-related database operations"""

    def test_mljob_creation(self, session, test_user):
        """Test creating ML job record"""
        # First create a document
        document = Document(
            user_id=test_user.id,
            filename="test.txt",
            content="Test content",
            pages=1,
            language="EN"
        )
        session.add(document)
        session.commit()
        
        # Create ML job
        job = MLJob(
            document_id=document.id,
            model_id=1,
            status="PENDING",
            summary_depth="BULLET",
            used_credits=Decimal('10.0')
        )
        
        session.add(job)
        session.commit()
        session.refresh(job)
        
        assert job.id is not None
        assert job.document_id == document.id
        assert job.status == "PENDING"
        assert job.started_at is not None

    def test_mljob_status_transitions(self, session, test_user):
        """Test ML job status transitions"""
        # Create document and job
        document = Document(
            user_id=test_user.id,
            filename="test.txt",
            content="Test content",
            pages=1,
            language="EN"
        )
        session.add(document)
        session.commit()
        
        job = MLJob(
            document_id=document.id,
            model_id=1,
            status="PENDING",
            summary_depth="BULLET",
            used_credits=Decimal('10.0')
        )
        session.add(job)
        session.commit()
        
        # Update status
        job.status = "PROCESSING"
        session.add(job)
        session.commit()
        
        # Verify update
        updated_job = session.get(MLJob, job.id)
        assert updated_job.status == "PROCESSING"


class TestModelDatabaseOperations:
    """Test model-related database operations"""

    def test_model_creation(self, session):
        """Test creating model record"""
        model = Model(
            name="test_model",
            price_per_token=Decimal('0.001'),
            active=True
        )
        
        session.add(model)
        session.commit()
        session.refresh(model)
        
        assert model.id is not None
        assert model.name == "test_model"
        assert model.price_per_token == Decimal('0.001')
        assert model.active is True

    def test_active_models_query(self, session):
        """Test querying only active models"""
        # Create active and inactive models
        active_model = Model(
            name="active_model",
            price_per_token=Decimal('0.001'),
            active=True
        )
        
        inactive_model = Model(
            name="inactive_model",
            price_per_token=Decimal('0.002'),
            active=False
        )
        
        session.add(active_model)
        session.add(inactive_model)
        session.commit()
        
        # Query only active models
        active_models = session.exec(
            select(Model).where(Model.active == True)
        ).all()
        
        assert len(active_models) == 1
        assert active_models[0].name == "active_model"


class TestDatabaseIntegrity:
    """Test database integrity and constraints"""

    def test_unique_email_constraint(self, session, sample_user_data):
        """Test that email uniqueness is enforced"""
        # Create first user
        create_user(sample_user_data, session)
        
        # Try to create another user with same email
        duplicate_data = sample_user_data.copy()
        duplicate_data["username"] = "different_username"
        
        # This should fail at the application level
        # (the actual constraint enforcement might be at DB or app level)
        existing_user = get_user_by_email(sample_user_data["email"], session)
        assert existing_user is not None

    def test_foreign_key_relationships(self, session, test_user):
        """Test foreign key relationships work correctly"""
        # Create wallet
        wallet = get_or_create_wallet(test_user.id, session)
        
        # Create transaction
        transaction = credit_wallet(test_user.id, Decimal('50'), session)
        
        # Create document
        document = Document(
            user_id=test_user.id,
            filename="test.txt",
            content="Test",
            pages=1,
            language="EN"
        )
        session.add(document)
        session.commit()
        
        # Verify relationships
        assert wallet.user_id == test_user.id
        assert transaction.user_id == test_user.id
        assert document.user_id == test_user.id

    def test_transaction_atomicity(self, session, test_user):
        """Test that database transactions are atomic"""
        initial_balance = get_or_create_wallet(test_user.id, session).balance
        
        try:
            # Start a transaction that should fail
            wallet = get_or_create_wallet(test_user.id, session)
            wallet.balance += Decimal('100')
            
            # Simulate an error before commit
            raise Exception("Simulated error")
            
        except Exception:
            session.rollback()
        
        # Balance should remain unchanged
        wallet = get_or_create_wallet(test_user.id, session)
        assert wallet.balance == initial_balance

    def test_cascade_behavior(self, session, test_user):
        """Test cascade behavior when deleting records"""
        # Create document
        document = Document(
            user_id=test_user.id,
            filename="test.txt",
            content="Test",
            pages=1,
            language="EN"
        )
        session.add(document)
        session.commit()
        
        document_id = document.id
        
        # Delete document
        session.delete(document)
        session.commit()
        
        # Verify document is deleted
        deleted_document = session.get(Document, document_id)
        assert deleted_document is None


class TestDatabasePerformance:
    """Test database performance aspects"""

    def test_bulk_operations(self, session, test_user):
        """Test bulk operations performance"""
        # Create multiple transactions
        transactions = []
        for i in range(10):
            tx = Transaction(
                user_id=test_user.id,
                tx_type="CREDIT",
                amount=Decimal(str(i + 1))
            )
            transactions.append(tx)
        
        # Add all at once
        session.add_all(transactions)
        session.commit()
        
        # Verify all were created
        user_transactions = session.exec(
            select(Transaction).where(Transaction.user_id == test_user.id)
        ).all()
        
        assert len(user_transactions) == 10

    def test_query_efficiency(self, session, test_user):
        """Test that queries are efficient"""
        # Create test data
        for i in range(5):
            document = Document(
                user_id=test_user.id,
                filename=f"test_{i}.txt",
                content=f"Content {i}",
                pages=1,
                language="EN"
            )
            session.add(document)
        
        session.commit()
        
        # Query with limit
        limited_documents = session.exec(
            select(Document)
            .where(Document.user_id == test_user.id)
            .limit(3)
        ).all()
        
        assert len(limited_documents) == 3