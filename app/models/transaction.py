from datetime import datetime
from decimal import Decimal
# from models.other import TxType
from sqlmodel import SQLModel, Field
# from sqlalchemy import Column, Enum as SQLEnum


class Transaction(SQLModel, table=True):
    """
    Движение средств в кошельке пользователя.

    Attributes:
        id (int): Уникальный идентификатор транзакции.
        user_id (int): ID пользователя, к которому относится транзакция.
        tx_type (TxType): CREDIT (зачисление) или DEBIT (списание).
        amount (Decimal): Сумма операции в кредитах (без знака).
        trans_time (datetime): Момент совершения операции.
    """
    id: int = Field(default=None, primary_key=True)
    user_id: int
    tx_type: str
    amount: Decimal
    trans_time: datetime = Field(default_factory=datetime.now)
