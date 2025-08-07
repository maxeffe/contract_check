from decimal import Decimal
from typing import Union
from models.user import User
# from models.other import Role
from models.transaction import Transaction
from sqlmodel import SQLModel, Field


class Admin:
    """Администратор — обертка вокруг User c дополнительными полномочиями."""

    def __init__(self, user_id: int, username: str, email: str, password: str):
        self.user = User(
            username=username,  
            email=email, 
            password=password,
            role="ADMIN"
        )
        self.user.id = user_id
    
    @property
    def username(self):
        return self.user.username
    
    @property 
    def email(self):
        return self.user.email
        
    @property
    def role(self):
        return self.user.role

    def credit_user(self, wallet, amount: Union[int, Decimal],
                    note: str = "admin_topup") -> Transaction:
        """Администратор может пополнить кошелек пользователя"""
        return wallet.credit(amount, note)
