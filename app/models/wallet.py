from decimal import Decimal
from typing import List, Union

from models.transaction import Transaction
# from models.other import TxType
from sqlmodel import SQLModel, Field

class Wallet(SQLModel, table=True):
    """
    Кошелек пользователя для управления балансом и транзакциями.

    Attributes:
        user_id (int): ID пользователя, которому принадлежит кошелек.
        _balance (Decimal): Текущий баланс в кредитах.
        transactions (List[Transaction]): История операций.
    """
    id: int = Field(default=None, primary_key=True)
    user_id: int
    balance: Decimal = Field(default=Decimal("0"))
    
    # Список транзакций не в таблице - создается при использовании

    def get_balance(self) -> Decimal:
        return self.balance

    def get_transactions(self) -> List[Transaction]:
        if not hasattr(self, '_transactions'):
            self._transactions = []
        return self._transactions

    def _add_tx(self, tx: Transaction) -> None:
        transactions = self.get_transactions()
        transactions.append(tx)
        if tx.tx_type == "CREDIT":
            self.balance += tx.amount
        elif tx.tx_type == "DEBIT":
            self.balance -= tx.amount

    def credit(self, amount: Union[int, Decimal], ref: str = "topup") -> Transaction:
        amount = Decimal(str(amount))
        tx = Transaction(
            id=len(self.get_transactions()) + 1,
            user_id=self.user_id,
            tx_type="CREDIT",
            amount=amount
        )
        self._add_tx(tx)
        return tx

    def debit(self, amount: Union[int, Decimal], ref: str) -> Transaction:
        amount = Decimal(str(amount))
        if self.balance < amount:
            raise ValueError(f"Insufficient balance:"
                             f"{self.balance} < {amount}")

        tx = Transaction(
            id=len(self.get_transactions()) + 1,
            user_id=self.user_id,
            tx_type="DEBIT",
            amount=amount
        )
        self._add_tx(tx)
        return tx
