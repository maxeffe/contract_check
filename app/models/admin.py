from decimal import Decimal
from typing import Union
from models.user import User
from models.other import Role
from models.transaction import Transaction


class Admin(User):
    """Администратор — наследник User c дополнительными полномочиями."""

    def __init__(self, user_id: int, username: str, email: str, password: str):
        super().__init__(id=user_id, username=username,
                         email=email, password=password,
                         role=Role.ADMIN)

    def credit_user(self, other: User, amount: Union[int, Decimal],
                    note: str = "admin_topup") -> Transaction:
        return other.credit(amount, note)
