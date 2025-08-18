import pytest
from decimal import Decimal
from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from services.crud.user import create_user
from services.crud.wallet import (
    get_wallet_by_user_id,
    create_wallet_for_user,
    get_or_create_wallet,
    update_wallet_balance,
    credit_wallet,
    debit_wallet,
    create_transaction,
    get_user_transactions,
    count_user_transactions
)


class TestWalletCreation:
    def test_create_wallet_for_user(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        wallet = create_wallet_for_user(user.id, session)
        
        assert wallet.id is not None
        assert wallet.user_id == user.id
        assert wallet.balance == Decimal("0")

    def test_get_or_create_wallet_new(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        wallet = get_or_create_wallet(user.id, session)
        
        assert wallet.id is not None
        assert wallet.user_id == user.id
        assert wallet.balance == Decimal("0")

    def test_get_or_create_wallet_existing(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        first_wallet = create_wallet_for_user(user.id, session)
        
        second_wallet = get_or_create_wallet(user.id, session)
        
        assert first_wallet.id == second_wallet.id
        assert first_wallet.user_id == second_wallet.user_id

    def test_get_wallet_by_user_id(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        created_wallet = create_wallet_for_user(user.id, session)
        
        retrieved_wallet = get_wallet_by_user_id(user.id, session)
        
        assert retrieved_wallet is not None
        assert retrieved_wallet.id == created_wallet.id
        assert retrieved_wallet.user_id == user.id

    def test_get_wallet_nonexistent_user(self, session):
        wallet = get_wallet_by_user_id(999, session)
        assert wallet is None


class TestWalletBalance:
    def test_update_wallet_balance(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        wallet = create_wallet_for_user(user.id, session)
        
        new_balance = Decimal("100.50")
        updated_wallet = update_wallet_balance(wallet.id, new_balance, session)
        
        assert updated_wallet.balance == new_balance

    def test_update_nonexistent_wallet_balance(self, session):
        updated_wallet = update_wallet_balance(999, Decimal("100"), session)
        assert updated_wallet is None


class TestWalletCredit:
    def test_credit_wallet_new_user(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        amount = Decimal("50.00")
        
        transaction = credit_wallet(user.id, amount, session)
        
        assert transaction.tx_type == "CREDIT"
        assert transaction.amount == amount
        assert transaction.user_id == user.id
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == amount

    def test_credit_wallet_existing_balance(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        first_amount = Decimal("30.00")
        credit_wallet(user.id, first_amount, session)
        
        second_amount = Decimal("20.00")
        transaction = credit_wallet(user.id, second_amount, session)
        
        assert transaction.amount == second_amount
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == first_amount + second_amount

    def test_credit_wallet_zero_amount(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        amount = Decimal("0")
        
        transaction = credit_wallet(user.id, amount, session)
        
        assert transaction.amount == amount
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == Decimal("0")

    def test_credit_wallet_large_amount(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        amount = Decimal("999999.99")
        
        transaction = credit_wallet(user.id, amount, session)
        
        assert transaction.amount == amount
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == amount


class TestWalletDebit:
    def test_debit_wallet_sufficient_balance(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        credit_amount = Decimal("100.00")
        credit_wallet(user.id, credit_amount, session)
        
        debit_amount = Decimal("30.00")
        transaction = debit_wallet(user.id, debit_amount, session)
        
        assert transaction.tx_type == "DEBIT"
        assert transaction.amount == debit_amount
        assert transaction.user_id == user.id
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == credit_amount - debit_amount

    def test_debit_wallet_insufficient_balance(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        credit_wallet(user.id, Decimal("10.00"), session)
        
        debit_amount = Decimal("50.00")
        
        with pytest.raises(ValueError, match="Insufficient balance"):
            debit_wallet(user.id, debit_amount, session)

    def test_debit_wallet_exact_balance(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        amount = Decimal("100.00")
        credit_wallet(user.id, amount, session)
        
        transaction = debit_wallet(user.id, amount, session)
        
        assert transaction.amount == amount
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == Decimal("0")

    def test_debit_wallet_zero_balance(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        with pytest.raises(ValueError, match="Insufficient balance"):
            debit_wallet(user.id, Decimal("1.00"), session)


class TestTransactionOperations:
    def test_create_transaction_credit(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        amount = Decimal("50.00")
        
        transaction = create_transaction(user.id, "CREDIT", amount, session)
        
        assert transaction.id is not None
        assert transaction.user_id == user.id
        assert transaction.tx_type == "CREDIT"
        assert transaction.amount == amount
        assert transaction.trans_time is not None

    def test_create_transaction_debit(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        amount = Decimal("25.00")
        
        transaction = create_transaction(user.id, "DEBIT", amount, session)
        
        assert transaction.tx_type == "DEBIT"
        assert transaction.amount == amount

    def test_get_user_transactions(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        credit_wallet(user.id, Decimal("100.00"), session)
        debit_wallet(user.id, Decimal("30.00"), session)
        credit_wallet(user.id, Decimal("50.00"), session)
        
        transactions = get_user_transactions(user.id, session)
        
        assert len(transactions) == 3

        assert transactions[0].trans_time >= transactions[1].trans_time
        assert transactions[1].trans_time >= transactions[2].trans_time

    def test_get_user_transactions_pagination(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        

        for i in range(5):
            credit_wallet(user.id, Decimal(f"{i + 1}0.00"), session)
        

        transactions = get_user_transactions(user.id, session, skip=0, limit=3)
        assert len(transactions) == 3

        transactions = get_user_transactions(user.id, session, skip=3, limit=3)
        assert len(transactions) == 2

    def test_get_user_transactions_empty(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        transactions = get_user_transactions(user.id, session)
        assert len(transactions) == 0

    def test_count_user_transactions(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        assert count_user_transactions(user.id, session) == 0
        

        credit_wallet(user.id, Decimal("100.00"), session)
        debit_wallet(user.id, Decimal("30.00"), session)
        
        assert count_user_transactions(user.id, session) == 2


class TestWalletIntegration:
    def test_multiple_operations_balance_consistency(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        credit_wallet(user.id, Decimal("100.00"), session)  
        debit_wallet(user.id, Decimal("25.00"), session)    
        credit_wallet(user.id, Decimal("50.00"), session)   
        debit_wallet(user.id, Decimal("75.00"), session)    
        
        wallet = get_wallet_by_user_id(user.id, session)
        assert wallet.balance == Decimal("50.00")
        

        assert count_user_transactions(user.id, session) == 4

    def test_multiple_users_isolation(self, session, sample_user_data, sample_admin_data):
        user1 = create_user(sample_user_data, session)
        user2 = create_user(sample_admin_data, session)
        

        credit_wallet(user1.id, Decimal("100.00"), session)
        debit_wallet(user1.id, Decimal("30.00"), session)
        
        
        credit_wallet(user2.id, Decimal("200.00"), session)
        
        
        wallet1 = get_wallet_by_user_id(user1.id, session)
        wallet2 = get_wallet_by_user_id(user2.id, session)
        
        assert wallet1.balance == Decimal("70.00")
        assert wallet2.balance == Decimal("200.00")
        
        
        transactions1 = get_user_transactions(user1.id, session)
        transactions2 = get_user_transactions(user2.id, session)
        
        assert len(transactions1) == 2
        assert len(transactions2) == 1