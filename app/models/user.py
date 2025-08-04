from decimal import Decimal
from typing import Optional, Union
import re
import bcrypt
# from models.other import Role
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.wallet import Wallet
    from models.transaction import Transaction
from sqlmodel import SQLModel, Field
# from sqlalchemy import Column, Enum as SQLEnum


class User(SQLModel, table=True):
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
    id: int = Field(default=None, primary_key=True)
    username: str
    email: str
    password: str
    role: str = Field(default="USER")

    def model_post_init(self, __context) -> None:
        self._validate_email()
        self._validate_password()
        # Wallet создается отдельно при необходимости

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

    # Методы для работы с кошельком будут добавлены позже
