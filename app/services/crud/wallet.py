from models.wallet import Wallet
from models.transaction import Transaction
from sqlmodel import Session, select
from typing import List, Optional
from decimal import Decimal

def get_wallet_by_user_id(user_id: int, session: Session) -> Optional[Wallet]:
    """Получить кошелек пользователя по ID"""
    statement = select(Wallet).where(Wallet.user_id == user_id)
    result = session.exec(statement)
    return result.first()

def create_wallet_for_user(user_id: int, session: Session) -> Wallet:
    """Создать кошелек для пользователя"""
    wallet = Wallet(user_id=user_id, balance=Decimal("0"))
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet

def get_or_create_wallet(user_id: int, session: Session) -> Wallet:
    """Получить кошелек пользователя или создать если не существует"""
    wallet = get_wallet_by_user_id(user_id, session)
    if not wallet:
        wallet = create_wallet_for_user(user_id, session)
    return wallet

def update_wallet_balance(wallet_id: int, new_balance: Decimal, session: Session) -> Optional[Wallet]:
    """Обновить баланс кошелька"""
    statement = select(Wallet).where(Wallet.id == wallet_id)
    result = session.exec(statement)
    wallet = result.first()
    
    if not wallet:
        return None
    
    wallet.balance = new_balance
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet

def create_transaction(
    user_id: int, 
    tx_type: str, 
    amount: Decimal, 
    session: Session
) -> Transaction:
    """Создать новую транзакцию"""
    transaction = Transaction(
        user_id=user_id,
        tx_type=tx_type,
        amount=amount
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction

def get_user_transactions(
    user_id: int, 
    session: Session, 
    skip: int = 0, 
    limit: int = 100
) -> List[Transaction]:
    """Получить транзакции пользователя с пагинацией"""
    statement = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.trans_time.desc())
        .offset(skip)
        .limit(limit)
    )
    result = session.exec(statement)
    return list(result.all())

def count_user_transactions(user_id: int, session: Session) -> int:
    """Подсчитать общее количество транзакций пользователя"""
    statement = select(Transaction).where(Transaction.user_id == user_id)
    result = session.exec(statement)
    return len(list(result.all()))

def credit_wallet(user_id: int, amount: Decimal, session: Session) -> Transaction:
    """Пополнить кошелек пользователя"""
    wallet = get_or_create_wallet(user_id, session)
    
    transaction = create_transaction(user_id, "CREDIT", amount, session)
    
    new_balance = wallet.balance + amount
    update_wallet_balance(wallet.id, new_balance, session)
    
    return transaction

def debit_wallet(user_id: int, amount: Decimal, session: Session) -> Transaction:
    """Списать средства с кошелька пользователя"""
    wallet = get_or_create_wallet(user_id, session)
    
    if wallet.balance < amount:
        raise ValueError(f"Insufficient balance: {wallet.balance} < {amount}")
    
    transaction = create_transaction(user_id, "DEBIT", amount, session)
    
    new_balance = wallet.balance - amount
    update_wallet_balance(wallet.id, new_balance, session)
    
    return transaction