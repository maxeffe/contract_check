import pytest
from fastapi import status
from decimal import Decimal
from services.crud.user import create_user
from services.crud.wallet import credit_wallet, debit_wallet


class TestWalletBalance:
    def test_get_balance_new_user(self, client, test_user_credentials, session):

        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        response = client.get("/wallet/balance", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["balance"] == "0"  

    def test_get_balance_no_auth(self, client):
        response = client.get("/wallet/balance")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_balance_invalid_token(self, client):
        response = client.get("/wallet/balance", headers={
            "Authorization": "Bearer invalid_token"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestWalletInfo:
    def test_get_wallet_info(self, client, test_user_credentials, session):

        user = create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        response = client.get("/wallet/wallet", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == user.id
        assert data["balance"] == "0"
        assert "id" in data

    def test_get_wallet_no_auth(self, client):
        response = client.get("/wallet/wallet")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTopUpBalance:
    def test_topup_success(self, client, test_user_credentials, session):

        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        topup_data = {"amount": "100.50"}
        response = client.post("/wallet/topup", 
                             json=topup_data,
                             headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Balance topped up successfully"
        assert data["amount"] == "100.50"
        assert "transaction_id" in data
        

        balance_response = client.get("/wallet/balance", headers={
            "Authorization": f"Bearer {token}"
        })
        assert balance_response.json()["balance"] == "100.50"

    def test_topup_zero_amount(self, client, test_user_credentials, session):
        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        topup_data = {"amount": "0"}
        response = client.post("/wallet/topup",
                             json=topup_data,
                             headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Amount must be positive"

    def test_topup_negative_amount(self, client, test_user_credentials, session):
        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        topup_data = {"amount": "-50.00"}
        response = client.post("/wallet/topup",
                             json=topup_data,
                             headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Amount must be positive"

    def test_topup_invalid_amount_format(self, client, test_user_credentials, session):
        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        topup_data = {"amount": "invalid"}
        response = client.post("/wallet/topup",
                             json=topup_data,
                             headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_topup_no_auth(self, client):
        topup_data = {"amount": "100.00"}
        response = client.post("/wallet/topup", json=topup_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_topup_large_amount(self, client, test_user_credentials, session):
        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        topup_data = {"amount": "999999.99"}
        response = client.post("/wallet/topup",
                             json=topup_data,
                             headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["amount"] == "999999.99"


class TestTransactionHistory:
    def test_get_transactions_empty(self, client, test_user_credentials, session):
        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        
        response = client.get("/wallet/transactions", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["transactions"] == []
        assert data["total_count"] == 0

    def test_get_transactions_with_data(self, client, test_user_credentials, session):
        user = create_user(test_user_credentials, session)
        

        credit_wallet(user.id, Decimal("100.00"), session)
        credit_wallet(user.id, Decimal("50.00"), session)
        debit_wallet(user.id, Decimal("25.00"), session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        
        response = client.get("/wallet/transactions", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["transactions"]) == 3
        assert data["total_count"] == 3
        

        for tx in data["transactions"]:
            assert "id" in tx
            assert "user_id" in tx
            assert "tx_type" in tx
            assert "amount" in tx
            assert "trans_time" in tx
            assert tx["user_id"] == user.id

    def test_get_transactions_pagination(self, client, test_user_credentials, session):
        user = create_user(test_user_credentials, session)
        

        for i in range(5):
            credit_wallet(user.id, Decimal(f"{i + 1}0.00"), session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        
      
        response = client.get("/wallet/transactions?skip=0&limit=3", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["transactions"]) == 3
        assert data["total_count"] == 5
        

        response = client.get("/wallet/transactions?skip=3&limit=3", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["transactions"]) == 2
        assert data["total_count"] == 5

    def test_get_transactions_invalid_pagination(self, client, test_user_credentials, session):
        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        response = client.get("/wallet/transactions?skip=-1", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        

        response = client.get("/wallet/transactions?limit=101", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_transactions_no_auth(self, client):
        response = client.get("/wallet/transactions")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestWalletIntegration:
    def test_complete_wallet_workflow(self, client, test_user_credentials, session):

        client.post("/auth/signup", json=test_user_credentials)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        

        balance_response = client.get("/wallet/balance", headers=headers)
        assert balance_response.json()["balance"] == "0"
        

        topup_response = client.post("/wallet/topup", 
                                   json={"amount": "100.00"}, 
                                   headers=headers)
        assert topup_response.status_code == status.HTTP_200_OK
        

        balance_response = client.get("/wallet/balance", headers=headers)
        assert balance_response.json()["balance"] == "100.00"
        

        wallet_response = client.get("/wallet/wallet", headers=headers)
        assert wallet_response.json()["balance"] == "100.00"
        

        tx_response = client.get("/wallet/transactions", headers=headers)
        assert len(tx_response.json()["transactions"]) == 1
        assert tx_response.json()["transactions"][0]["tx_type"] == "CREDIT"
        assert tx_response.json()["transactions"][0]["amount"] == "100.00"

    def test_multiple_topups(self, client, test_user_credentials, session):
        client.post("/auth/signup", json=test_user_credentials)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        

        amounts = ["50.00", "75.25", "100.75"]
        for amount in amounts:
            response = client.post("/wallet/topup", 
                                 json={"amount": amount}, 
                                 headers=headers)
            assert response.status_code == status.HTTP_200_OK
        

        balance_response = client.get("/wallet/balance", headers=headers)
        expected_total = sum(Decimal(amount) for amount in amounts)
        assert Decimal(balance_response.json()["balance"]) == expected_total
        

        tx_response = client.get("/wallet/transactions", headers=headers)
        assert len(tx_response.json()["transactions"]) == 3

    def test_user_isolation_wallets(self, client):

        user1_data = {
            "username": "user1_wallet",
            "email": "user1wallet@example.com",
            "password": "password123"
        }
        user2_data = {
            "username": "user2_wallet",
            "email": "user2wallet@example.com",
            "password": "password123"
        }
        

        client.post("/auth/signup", json=user1_data)
        client.post("/auth/signup", json=user2_data)
        

        login1 = client.post("/auth/signin", json={
            "email": user1_data["email"],
            "password": user1_data["password"]
        })
        token1 = login1.json()["access_token"]
        
        login2 = client.post("/auth/signin", json={
            "email": user2_data["email"],
            "password": user2_data["password"]
        })
        token2 = login2.json()["access_token"]
        

        client.post("/wallet/topup", 
                   json={"amount": "100.00"}, 
                   headers={"Authorization": f"Bearer {token1}"})
        
        client.post("/wallet/topup", 
                   json={"amount": "200.00"}, 
                   headers={"Authorization": f"Bearer {token2}"})
        

        balance1 = client.get("/wallet/balance", 
                            headers={"Authorization": f"Bearer {token1}"})
        balance2 = client.get("/wallet/balance", 
                            headers={"Authorization": f"Bearer {token2}"})
        
        assert balance1.json()["balance"] == "100.00"
        assert balance2.json()["balance"] == "200.00"
        

        tx1 = client.get("/wallet/transactions", 
                        headers={"Authorization": f"Bearer {token1}"})
        tx2 = client.get("/wallet/transactions", 
                        headers={"Authorization": f"Bearer {token2}"})
        
        assert len(tx1.json()["transactions"]) == 1
        assert len(tx2.json()["transactions"]) == 1
        assert tx1.json()["transactions"][0]["amount"] == "100.00"
        assert tx2.json()["transactions"][0]["amount"] == "200.00"