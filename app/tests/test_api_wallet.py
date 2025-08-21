import pytest
from fastapi import status
from decimal import Decimal

class TestWalletBalance:
    """Test wallet balance endpoints"""

    def test_get_balance_new_user(self, client, auth_headers):
        """Test getting balance for new user (should create wallet)"""
        response = client.get("/wallet/balance", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "balance" in data
        assert float(data["balance"]) == 0.0

    def test_get_balance_no_auth(self, client):
        """Test getting balance without authentication"""
        response = client.get("/wallet/balance")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestWalletInfo:
    """Test wallet information endpoints"""

    def test_get_wallet_info(self, client, auth_headers):
        """Test getting wallet information"""
        response = client.get("/wallet/wallet", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "user_id" in data
        assert "balance" in data
        assert "total_transactions" in data
        assert float(data["balance"]) == 0.0
        assert data["total_transactions"] == 0

    def test_get_wallet_no_auth(self, client):
        """Test getting wallet info without authentication"""
        response = client.get("/wallet/wallet")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTopUpBalance:
    """Test balance top-up functionality"""

    def test_topup_success(self, client, auth_headers):
        """Test successful balance top-up"""
        topup_data = {"amount": 100.0}
        response = client.post("/wallet/topup", json=topup_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Balance topped up successfully"
        assert data["amount"] == 100.0
        assert "transaction_id" in data
        
        # Verify balance was updated
        balance_response = client.get("/wallet/balance", headers=auth_headers)
        assert balance_response.status_code == status.HTTP_200_OK
        balance_data = balance_response.json()
        assert float(balance_data["balance"]) == 100.0

    def test_topup_zero_amount(self, client, auth_headers):
        """Test top-up with zero amount"""
        topup_data = {"amount": 0}
        response = client.post("/wallet/topup", json=topup_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Amount must be positive"

    def test_topup_negative_amount(self, client, auth_headers):
        """Test top-up with negative amount"""
        topup_data = {"amount": -50.0}
        response = client.post("/wallet/topup", json=topup_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Amount must be positive"

    def test_topup_invalid_amount_format(self, client, auth_headers):
        """Test top-up with invalid amount format"""
        topup_data = {"amount": "invalid"}
        response = client.post("/wallet/topup", json=topup_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_topup_no_auth(self, client):
        """Test top-up without authentication"""
        topup_data = {"amount": 100.0}
        response = client.post("/wallet/topup", json=topup_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_topup_large_amount(self, client, auth_headers):
        """Test top-up with large amount"""
        topup_data = {"amount": 999999.99}
        response = client.post("/wallet/topup", json=topup_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["amount"] == 999999.99


class TestTransactionHistory:
    """Test transaction history endpoints"""

    def test_get_transactions_empty(self, client, auth_headers):
        """Test getting transactions for new user (empty history)"""
        response = client.get("/wallet/transactions", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "transactions" in data
        assert "total_count" in data
        assert len(data["transactions"]) == 0
        assert data["total_count"] == 0

    def test_get_transactions_with_data(self, client, auth_headers):
        """Test getting transactions after making top-ups"""
        # Make a few top-ups to create transaction history
        client.post("/wallet/topup", json={"amount": 100.0}, headers=auth_headers)
        client.post("/wallet/topup", json={"amount": 50.0}, headers=auth_headers)
        
        response = client.get("/wallet/transactions", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["transactions"]) == 2
        assert data["total_count"] == 2
        
        # Check transaction details
        for transaction in data["transactions"]:
            assert "id" in transaction
            assert "user_id" in transaction
            assert "tx_type" in transaction
            assert "amount" in transaction
            assert "trans_time" in transaction
            assert transaction["tx_type"] == "CREDIT"

    def test_get_transactions_pagination(self, client, auth_headers):
        """Test transaction pagination"""
        # Create multiple transactions
        for i in range(5):
            client.post("/wallet/topup", json={"amount": 10.0 * (i + 1)}, headers=auth_headers)
        
        # Test pagination
        response = client.get("/wallet/transactions?limit=2&skip=0", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["transactions"]) == 2
        assert data["total_count"] == 5
        
        # Test second page
        response2 = client.get("/wallet/transactions?limit=2&skip=2", headers=auth_headers)
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert len(data2["transactions"]) == 2

    def test_get_transactions_invalid_pagination(self, client, auth_headers):
        """Test invalid pagination parameters"""
        # Negative skip
        response = client.get("/wallet/transactions?skip=-1", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Too large limit
        response = client.get("/wallet/transactions?limit=1000", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Zero limit
        response = client.get("/wallet/transactions?limit=0", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_transactions_no_auth(self, client):
        """Test getting transactions without authentication"""
        response = client.get("/wallet/transactions")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestWalletIntegration:
    """Test wallet integration scenarios"""

    def test_complete_wallet_workflow(self, client, auth_headers):
        """Test complete wallet workflow"""
        # 1. Get initial balance (should be 0)
        balance_response = client.get("/wallet/balance", headers=auth_headers)
        assert balance_response.json()["balance"] == 0
        
        # 2. Top up balance
        topup_response = client.post("/wallet/topup", json={"amount": 150.0}, headers=auth_headers)
        assert topup_response.status_code == status.HTTP_200_OK
        
        # 3. Check balance updated
        balance_response = client.get("/wallet/balance", headers=auth_headers)
        assert float(balance_response.json()["balance"]) == 150.0
        
        # 4. Check wallet info
        wallet_response = client.get("/wallet/wallet", headers=auth_headers)
        wallet_data = wallet_response.json()
        assert float(wallet_data["balance"]) == 150.0
        assert wallet_data["total_transactions"] == 1
        
        # 5. Check transaction history
        transactions_response = client.get("/wallet/transactions", headers=auth_headers)
        transactions_data = transactions_response.json()
        assert len(transactions_data["transactions"]) == 1
        assert transactions_data["transactions"][0]["amount"] == 150.0
        assert transactions_data["transactions"][0]["tx_type"] == "CREDIT"

    def test_multiple_topups(self, client, auth_headers):
        """Test multiple top-ups accumulate correctly"""
        amounts = [50.0, 25.0, 100.0, 10.0]
        
        for amount in amounts:
            response = client.post("/wallet/topup", json={"amount": amount}, headers=auth_headers)
            assert response.status_code == status.HTTP_200_OK
        
        # Check final balance
        balance_response = client.get("/wallet/balance", headers=auth_headers)
        expected_balance = sum(amounts)
        assert float(balance_response.json()["balance"]) == expected_balance
        
        # Check transaction count
        wallet_response = client.get("/wallet/wallet", headers=auth_headers)
        assert wallet_response.json()["total_transactions"] == len(amounts)

    def test_user_isolation_wallets(self, client):
        """Test that users have isolated wallets"""
        # Create two users and their auth headers
        user1_data = {
            "username": "user1",
            "email": "user1@example.com",
            "password": "password123"
        }
        user2_data = {
            "username": "user2",
            "email": "user2@example.com", 
            "password": "password123"
        }
        
        # Register users
        client.post("/auth/signup", json=user1_data)
        client.post("/auth/signup", json=user2_data)
        
        # Login users
        login1 = client.post("/auth/signin", json={
            "email": user1_data["email"],
            "password": user1_data["password"]
        })
        login2 = client.post("/auth/signin", json={
            "email": user2_data["email"], 
            "password": user2_data["password"]
        })
        
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}
        
        # Top up user1 wallet
        client.post("/wallet/topup", json={"amount": 100.0}, headers=headers1)
        
        # Check balances are isolated
        balance1 = client.get("/wallet/balance", headers=headers1)
        balance2 = client.get("/wallet/balance", headers=headers2)
        
        assert float(balance1.json()["balance"]) == 100.0
        assert float(balance2.json()["balance"]) == 0.0
        
        # Check wallet info isolation
        wallet1 = client.get("/wallet/wallet", headers=headers1)
        wallet2 = client.get("/wallet/wallet", headers=headers2)
        
        assert wallet1.json()["user_id"] != wallet2.json()["user_id"]
        assert wallet1.json()["total_transactions"] == 1
        assert wallet2.json()["total_transactions"] == 0


class TestWalletEdgeCases:
    """Test wallet edge cases and error scenarios"""

    def test_concurrent_topups_simulation(self, client, auth_headers):
        """Test simulation of concurrent top-ups"""
        # Simulate concurrent requests by making multiple rapid requests
        amounts = [10.0, 20.0, 30.0, 40.0, 50.0]
        responses = []
        
        for amount in amounts:
            response = client.post("/wallet/topup", json={"amount": amount}, headers=auth_headers)
            responses.append(response)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
        
        # Final balance should be sum of all amounts
        balance_response = client.get("/wallet/balance", headers=auth_headers)
        expected_balance = sum(amounts)
        assert float(balance_response.json()["balance"]) == expected_balance

    def test_decimal_precision(self, client, auth_headers):
        """Test decimal precision in amounts"""
        # Top up with precise decimal amount
        precise_amount = 123.456789
        response = client.post("/wallet/topup", json={"amount": precise_amount}, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check balance maintains reasonable precision
        balance_response = client.get("/wallet/balance", headers=auth_headers)
        balance = float(balance_response.json()["balance"])
        
        # Should be approximately equal (allowing for floating point precision)
        assert abs(balance - precise_amount) < 0.01

    def test_topup_missing_amount_field(self, client, auth_headers):
        """Test top-up with missing amount field"""
        response = client.post("/wallet/topup", json={}, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY