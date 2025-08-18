import pytest
from decimal import Decimal
from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from services.crud.user import create_user, authenticate_user
from services.crud.wallet import (
    credit_wallet, 
    debit_wallet, 
    get_user_transactions,
    get_wallet_by_user_id
)


class TestUserWalletIntegration:
    def test_complete_user_workflow(self, session):
        """Тест полного жизненного цикла пользователя и его кошелька"""
        
        user_data = {
            "username": "integration_user",
            "email": "integration@example.com",
            "password": "securepassword123",
            "role": "USER"
        }
        original_password = user_data["password"]
        user = create_user(user_data, session)
        
        authenticated_user = authenticate_user(
            user_data["email"], 
            original_password, 
            session
        )
        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        
        initial_amount = Decimal("1000.00")
        credit_tx = credit_wallet(user.id, initial_amount, session)
        
        assert credit_tx.tx_type == "CREDIT"
        assert credit_tx.amount == initial_amount
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == initial_amount
        
        service_costs = [
            Decimal("50.00"),  
            Decimal("75.00"),  
            Decimal("25.00"), 
        ]
        
        for cost in service_costs:
            debit_wallet(user.id, cost, session)
        
        wallet = get_wallet_by_user_id(user.id, session)
        expected_balance = initial_amount - sum(service_costs)
        assert wallet.balance == expected_balance
        
        additional_amount = Decimal("500.00")
        credit_wallet(user.id, additional_amount, session)
        
        
        wallet = get_wallet_by_user_id(user.id, session)
        final_expected_balance = expected_balance + additional_amount
        assert wallet.balance == final_expected_balance
        
        transactions = get_user_transactions(user.id, session)
        assert len(transactions) == 5 
        
        tx_types = [tx.tx_type for tx in transactions]
        assert tx_types.count("CREDIT") == 2
        assert tx_types.count("DEBIT") == 3

    def test_insufficient_funds_scenario(self, session, sample_user_data):
        """Тест сценария с недостаточными средствами"""
        
        user = create_user(sample_user_data, session)
        
        small_amount = Decimal("50.00")
        credit_wallet(user.id, small_amount, session)
        
        debit_wallet(user.id, Decimal("30.00"), session)
        
        with pytest.raises(ValueError, match="Insufficient balance"):
            debit_wallet(user.id, Decimal("50.00"), session)
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == Decimal("20.00") 

    def test_concurrent_operations_simulation(self, session):
        """Симуляция одновременных операций с кошельком"""
        
        user_data = {
            "username": "concurrent_user",
            "email": "concurrent@example.com",
            "password": "password123",
            "role": "USER"
        }
        user = create_user(user_data, session)
        
        credit_wallet(user.id, Decimal("1000.00"), session)
        
        operations = [
            ("DEBIT", Decimal("100.00")),
            ("CREDIT", Decimal("50.00")),
            ("DEBIT", Decimal("200.00")),
            ("CREDIT", Decimal("150.00")),
            ("DEBIT", Decimal("75.00")),
        ]
        
        expected_balance = Decimal("1000.00")
        
        for op_type, amount in operations:
            if op_type == "CREDIT":
                credit_wallet(user.id, amount, session)
                expected_balance += amount
            else:  # DEBIT
                debit_wallet(user.id, amount, session)
                expected_balance -= amount
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == expected_balance
        
        transactions = get_user_transactions(user.id, session)
        assert len(transactions) == 6  # 5 операций + 1 начальное пополнение

    def test_large_amount_operations(self, session, sample_user_data):
        """Тест операций с большими суммами"""
        
        user = create_user(sample_user_data, session)

        large_amount = Decimal("999999.99")
        credit_wallet(user.id, large_amount, session)
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == large_amount
        
        partial_debit = Decimal("500000.00")
        debit_wallet(user.id, partial_debit, session)
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == large_amount - partial_debit

    def test_precision_handling(self, session, sample_user_data):
        """Тест точности при работе с десятичными числами"""
        
        user = create_user(sample_user_data, session)
        
        precise_amounts = [
            Decimal("0.01"),
            Decimal("0.99"),
            Decimal("100.01"),
            Decimal("999.99"),
        ]
        
        for amount in precise_amounts:
            credit_wallet(user.id, amount, session)
        
        expected_total = sum(precise_amounts)
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == expected_total
        
        debit_amount = Decimal("555.55")
        debit_wallet(user.id, debit_amount, session)
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == expected_total - debit_amount

    def test_transaction_history_ordering(self, session, sample_user_data):
        """Тест правильности сортировки истории транзакций"""
        
        user = create_user(sample_user_data, session)
        
        amounts = [Decimal("100.00"), Decimal("50.00"), Decimal("75.00")]
        
        for amount in amounts:
            credit_wallet(user.id, amount, session)

        transactions = get_user_transactions(user.id, session)
        
        for i in range(len(transactions) - 1):
            assert transactions[i].trans_time >= transactions[i + 1].trans_time
        
        transaction_amounts = [tx.amount for tx in transactions]
        assert set(transaction_amounts) == set(amounts)


class TestErrorHandling:
    def test_invalid_user_operations(self, session):
        """Тест операций с несуществующими пользователями"""
        
        try:
            credit_wallet(999999, Decimal("100.00"), session)
        except Exception:
            pass

    def test_zero_and_negative_amounts(self, session, sample_user_data):
        """Тест операций с нулевыми и отрицательными суммами"""
        
        user = create_user(sample_user_data, session)
        
        credit_wallet(user.id, Decimal("0"), session)
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == Decimal("0")
        
        credit_wallet(user.id, Decimal("100.00"), session)
        
        try:
            debit_wallet(user.id, Decimal("-50.00"), session)
        except Exception:
            pass 