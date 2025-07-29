from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Union
import re
import bcrypt
from models.other import Role
from models.wallet import Wallet
from models.transaction import Transaction


@dataclass
class User:
    """
    Учётная запись.

    Attributes:
        id (int): Идентификатор пользователя.
        username (str): Отображаемое имя / login.
        email (str): Адрес электронной почты.
        password (str): Хэш пароля.
        role (Role): USER или ADMIN.
        wallet (Wallet): Кошелек пользователя.
    """
    id: int
    username: str
    email: str
    password: str
    role: Role = Role.USER
    wallet: Optional[Wallet] = None

    def __post_init__(self) -> None:
        self._validate_email()
        self._validate_password()
        if self.wallet is None:
            self.wallet = Wallet(user_id=self.id)

    def _validate_email(self) -> None:
        if not re.fullmatch(r"^[\w\.-]+@[\w\.-]+\.\w+$", self.email):
            raise ValueError("Invalid email")

    def _validate_password(self) -> None:
        if len(self.password) < 8:
            raise ValueError("Password must be ≥ 8 chars")

    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширует пароль с использованием bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str) -> bool:
        """Проверяет соответствие пароля хешу."""
        return bcrypt.checkpw(password.encode('utf-8'),
                              self.password.encode('utf-8'))

    @property
    def balance(self) -> Decimal:
        """Текущий баланс пользователя (read‑only)."""
        return self.wallet.balance if self.wallet else Decimal("0")

    def credit(self, amount: Union[int, Decimal],
               ref: str = "topup") -> Transaction:
        """Зачисление средств."""
        return self.wallet.credit(amount, ref)

    def debit(self, amount: Union[int, Decimal], ref: str) -> Transaction:
        """Списание средств. Бросает ValueError при нехватке баланса."""
        return self.wallet.debit(amount, ref)
