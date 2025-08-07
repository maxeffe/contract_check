from pydantic import BaseModel
from decimal import Decimal
from typing import List
from datetime import datetime

class WalletResponse(BaseModel):
    id: int
    user_id: int
    balance: Decimal

class TransactionResponse(BaseModel):
    id: int
    user_id: int
    tx_type: str
    amount: Decimal
    trans_time: datetime

class TopUpRequest(BaseModel):
    amount: Decimal

class BalanceResponse(BaseModel):
    balance: Decimal

class TransactionHistoryResponse(BaseModel):
    transactions: List[TransactionResponse]
    total_count: int