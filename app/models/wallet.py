from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Union

from models.transaction import Transaction
from models.other import TxType


@dataclass
class Wallet:
    """
    Кошелек пользователя для управления балансом и транзакциями.

    Attributes:
        user_id (int): ID пользователя, которому принадлежит кошелек.
        _balance (Decimal): Текущий баланс в кредитах.
        transactions (List[Transaction]): История операций.
    """
    user_id: int
    _balance: Decimal = Decimal("0")
    transactions: List[Transaction] = field(default_factory=list)

    @property
    def balance(self) -> Decimal:
        return self._balance

    def _add_tx(self, tx: Transaction) -> None:
        self.transactions.append(tx)
        if tx.tx_type == TxType.CREDIT:
            self._balance += tx.amount
        elif tx.tx_type == TxType.DEBIT:
            self._balance -= tx.amount

    def credit(self, amount: Union[int, Decimal]) -> Transaction:
        amount = Decimal(str(amount))
        tx = Transaction(
            id=len(self.transactions) + 1,
            user_id=self.user_id,
            tx_type=TxType.CREDIT,
            amount=amount
        )
        self._add_tx(tx)
        return tx

    def debit(self, amount: Union[int, Decimal]) -> Transaction:
        amount = Decimal(str(amount))
        if self._balance < amount:
            raise ValueError(f"Insufficient balance:"
                             f"{self._balance} < {amount}")

        tx = Transaction(
            id=len(self.transactions) + 1,
            user_id=self.user_id,
            tx_type=TxType.DEBIT,
            amount=amount
        )
        self._add_tx(tx)
        return tx
