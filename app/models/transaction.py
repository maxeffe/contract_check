from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from models.other import TxType


@dataclass
class Transaction:
    """
    Движение средств в кошельке пользователя.

    Attributes:
        id (int): Уникальный идентификатор транзакции.
        user_id (int): ID пользователя, к которому относится транзакция.
        tx_type (TxType): CREDIT (зачисление) или DEBIT (списание).
        amount (Decimal): Сумма операции в кредитах (без знака).
        trans_time (datetime): Момент совершения операции.
    """
    id: int
    user_id: int
    tx_type: TxType
    amount: Decimal
    trans_time: datetime = field(default_factory=datetime.now)
