from fastapi import APIRouter, HTTPException, status, Depends, Query
from services.crud import wallet as WalletService
from database.database import get_session
from schemas.wallet import WalletResponse, BalanceResponse, TopUpRequest, TransactionHistoryResponse, TransactionResponse
from auth.jwt_handler import get_current_user
from typing import List
from config.logging_config import wallet_logger

wallet_route = APIRouter(tags=['Wallet'])

@wallet_route.get('/balance')
async def get_balance(
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> BalanceResponse:
    """Получить баланс текущего пользователя"""
    wallet = WalletService.get_or_create_wallet(current_user["user_id"], session)
    return BalanceResponse(balance=wallet.balance)

@wallet_route.post('/topup')
async def topup_balance(
    data: TopUpRequest,
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> dict:
    """Пополнить баланс"""
    if data.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    wallet_logger.info(f"Пополнение баланса пользователя {current_user['user_id']} на сумму {data.amount}")
    
    try:
        transaction = WalletService.credit_wallet(
            current_user["user_id"], 
            data.amount, 
            session
        )
        wallet_logger.info(f"Баланс пополнен успешно. Transaction ID: {transaction.id}")
        return {
            "message": "Balance topped up successfully",
            "amount": data.amount,
            "transaction_id": transaction.id
        }
    except Exception as e:
        wallet_logger.error(f"Ошибка пополнения баланса пользователя {current_user['user_id']}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to top up balance: {str(e)}"
        )

@wallet_route.get('/wallet')
async def get_wallet(
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> WalletResponse:
    """Получить информацию о кошельке"""
    wallet = WalletService.get_or_create_wallet(current_user["user_id"], session)
    
    total_transactions = WalletService.count_user_transactions(current_user["user_id"], session)
    
    return WalletResponse(
        id=wallet.id,
        user_id=wallet.user_id,
        balance=wallet.balance,
        total_transactions=total_transactions
    )

@wallet_route.get('/transactions')
async def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> TransactionHistoryResponse:
    """Получить историю транзакций с пагинацией"""
    transactions = WalletService.get_user_transactions(
        current_user["user_id"], 
        session, 
        skip, 
        limit
    )
    
    total_count = WalletService.count_user_transactions(
        current_user["user_id"], 
        session
    )
    
    transaction_responses = [
        TransactionResponse(
            id=tx.id,
            user_id=tx.user_id,
            tx_type=tx.tx_type,
            amount=tx.amount,
            trans_time=tx.trans_time
        ) for tx in transactions
    ]
    
    return TransactionHistoryResponse(
        transactions=transaction_responses,
        total_count=total_count
    )