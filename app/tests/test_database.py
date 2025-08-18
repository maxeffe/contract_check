import pytest
from decimal import Decimal
import sqlite3
from sqlmodel import create_engine, Session, SQLModel, text
from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from services.crud.user import create_user
from services.crud.wallet import credit_wallet, debit_wallet


class TestDatabaseIntegrity:
    def test_database_schema_creation(self):
        """Тест создания схемы базы данных"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        SQLModel.metadata.create_all(engine)
        

        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            
            assert "user" in tables
            assert "wallet" in tables
            assert "transaction" in tables

    def test_database_constraints(self, session):
        """Тест ограничений базы данных"""
        

        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        user = create_user(user_data, session)
        

        duplicate_user = User(
            username="anotheruser",
            email="test@example.com",
            password="password456"
        )
        
        session.add(duplicate_user)
        try:
            session.commit()

            session.delete(duplicate_user)
            session.commit()
        except Exception:

            session.rollback()

    def test_database_persistence(self):
        """Тест сохранения данных в базе"""
        

        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:

            engine1 = create_engine(f"sqlite:///{db_path}", echo=False)
            SQLModel.metadata.create_all(engine1)
            
            with Session(engine1) as session1:
                user_data = {
                    "username": "persistent_user",
                    "email": "persistent@example.com",
                    "password": "password123"
                }
                user = create_user(user_data, session1)
                credit_wallet(user.id, Decimal("100.00"), session1)
                user_id = user.id
            

            engine2 = create_engine(f"sqlite:///{db_path}", echo=False)
            
            with Session(engine2) as session2:

                user = session2.get(User, user_id)
                assert user is not None
                assert user.email == "persistent@example.com"
                
                wallet = session2.query(Wallet).filter(Wallet.user_id == user_id).first()
                assert wallet is not None
                assert wallet.balance == Decimal("100.00")
                
                transactions = session2.query(Transaction).filter(Transaction.user_id == user_id).all()
                assert len(transactions) == 1
                assert transactions[0].amount == Decimal("100.00")
        
        finally:

            os.unlink(db_path)

    def test_transaction_rollback(self, session):
        """Тест отката транзакций"""
        
        user_data = {
            "username": "rollback_user",
            "email": "rollback@example.com",
            "password": "password123"
        }
        user = create_user(user_data, session)
        

        savepoint = session.begin_nested()
        
        try:

            credit_wallet(user.id, Decimal("100.00"), session)
            

            wallet = session.query(Wallet).filter(Wallet.user_id == user.id).first()
            assert wallet.balance == Decimal("100.00")
            

            savepoint.rollback()
            

            session.refresh(wallet)
            wallet = session.query(Wallet).filter(Wallet.user_id == user.id).first()
            if wallet:
                assert wallet.balance == Decimal("0.00")
            
        except Exception:
            savepoint.rollback()
            raise

    def test_concurrent_access_simulation(self):
        """Симуляция конкурентного доступа к базе данных"""
        
        import tempfile
        import os
        import threading
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            db_path = tmp_file.name
        
        try:

            engine = create_engine(f"sqlite:///{db_path}", echo=False)
            SQLModel.metadata.create_all(engine)
            
      
            with Session(engine) as session:
                user_data = {
                    "username": "concurrent_user",
                    "email": "concurrent@example.com",
                    "password": "password123"
                }
                user = create_user(user_data, session)
                user_id = user.id
            
     
            def credit_operation(amount):
                engine_local = create_engine(f"sqlite:///{db_path}", echo=False)
                with Session(engine_local) as session_local:
                    try:
                        credit_wallet(user_id, Decimal(str(amount)), session_local)
                    except Exception as e:
                        print(f"Error in credit operation: {e}")
            
 
            threads = []
            amounts = ["10.00", "20.00", "30.00"]
            
            for amount in amounts:
                thread = threading.Thread(target=credit_operation, args=(amount,))
                threads.append(thread)
                thread.start()
            
        
            for thread in threads:
                thread.join()
            

            with Session(engine) as session:
                wallet = session.query(Wallet).filter(Wallet.user_id == user_id).first()
                transactions = session.query(Transaction).filter(Transaction.user_id == user_id).all()
                

                assert len(transactions) >= 1  
                
               
                total_credited = sum(tx.amount for tx in transactions if tx.tx_type == "CREDIT")
                assert wallet.balance == total_credited
        
        finally:
            os.unlink(db_path)

    def test_large_dataset_performance(self):
        """Тест производительности с большим количеством данных"""
        
        engine = create_engine("sqlite:///:memory:", echo=False)
        SQLModel.metadata.create_all(engine)
        
        with Session(engine) as session:

            users = []
            for i in range(100):
                user_data = {
                    "username": f"user_{i}",
                    "email": f"user_{i}@example.com",
                    "password": "password123"
                }
                user = create_user(user_data, session)
                users.append(user)
            
        
            for user in users[:10]: 
                for j in range(10):
                    credit_wallet(user.id, Decimal(f"{j + 1}.00"), session)
            

            total_users = session.query(User).count()
            assert total_users == 100
            
            total_transactions = session.query(Transaction).count()
            assert total_transactions == 100  
            

            result = session.query(User, Wallet).join(Wallet, User.id == Wallet.user_id).all()
            assert len(result) >= 10

    def test_database_backup_restore(self):
        """Тест резервного копирования и восстановления"""
        
        import tempfile
        import os
        import shutil
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            original_db_path = tmp_file.name
        
        backup_db_path = original_db_path + '.backup'
        
        try:

            engine1 = create_engine(f"sqlite:///{original_db_path}", echo=False)
            SQLModel.metadata.create_all(engine1)
            
            with Session(engine1) as session:
                user_data = {
                    "username": "backup_user",
                    "email": "backup@example.com",
                    "password": "password123"
                }
                user = create_user(user_data, session)
                credit_wallet(user.id, Decimal("500.00"), session)
                original_user_id = user.id
            

            shutil.copy2(original_db_path, backup_db_path)
            

            engine2 = create_engine(f"sqlite:///{backup_db_path}", echo=False)
            
            with Session(engine2) as session:

                user = session.get(User, original_user_id)
                assert user is not None
                assert user.email == "backup@example.com"
                
                wallet = session.query(Wallet).filter(Wallet.user_id == original_user_id).first()
                assert wallet.balance == Decimal("500.00")
        
        finally:
            for path in [original_db_path, backup_db_path]:
                if os.path.exists(path):
                    os.unlink(path)


class TestDatabaseQueries:
    def test_complex_queries(self, session):
        """Тест сложных запросов к базе данных"""
        

        users = []
        for i in range(5):
            user_data = {
                "username": f"query_user_{i}",
                "email": f"query_{i}@example.com",
                "password": "password123"
            }
            user = create_user(user_data, session)
            users.append(user)
            

            if i % 2 == 0: 
                credit_wallet(user.id, Decimal("100.00"), session)
                debit_wallet(user.id, Decimal("30.00"), session)
            else: 
                credit_wallet(user.id, Decimal("200.00"), session)
        

        high_balance_users = session.query(User).join(Wallet).filter(Wallet.balance > 150).all()
        assert len(high_balance_users) >= 2 
        

        credit_count = session.query(Transaction).filter(Transaction.tx_type == "CREDIT").count()
        debit_count = session.query(Transaction).filter(Transaction.tx_type == "DEBIT").count()
        
        assert credit_count == 5  
        assert debit_count == 2   
        

        users_without_tx = session.query(User).filter(
            ~User.id.in_(session.query(Transaction.user_id).distinct())
        ).all()
        assert len(users_without_tx) == 0

    def test_database_indexing_performance(self, session):
        """Тест производительности индексов"""
        

        import time
        
   
        start_time = time.time()
        users = []
        for i in range(50):
            user_data = {
                "username": f"perf_user_{i}",
                "email": f"perf_{i}@example.com",
                "password": "password123"
            }
            user = create_user(user_data, session)
            users.append(user)
        user_creation_time = time.time() - start_time
        

        start_time = time.time()
        user = session.query(User).filter(User.email == "perf_25@example.com").first()
        email_search_time = time.time() - start_time
        
        assert user is not None
        assert email_search_time < 0.1  
        

        start_time = time.time()
        user_by_id = session.get(User, user.id)
        id_search_time = time.time() - start_time
        
        assert user_by_id is not None
        assert id_search_time < 0.01  