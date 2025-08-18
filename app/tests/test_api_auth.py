import pytest
from fastapi import status
from services.crud.user import create_user


class TestUserRegistration:
    def test_signup_success(self, client, test_user_credentials):
        response = client.post("/auth/signup", json=test_user_credentials)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "User was created successfully"
        assert data["user"]["username"] == test_user_credentials["username"]
        assert data["user"]["email"] == test_user_credentials["email"]
        assert data["user"]["role"] == "USER"
        assert "id" in data["user"]

    def test_signup_duplicate_email(self, client, test_user_credentials, session):

        create_user(test_user_credentials, session)
        

        response = client.post("/auth/signup", json=test_user_credentials)
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "User already exists"

    def test_signup_invalid_email(self, client):
        invalid_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        }
        
        response = client.post("/auth/signup", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_missing_fields(self, client):
        incomplete_data = {
            "username": "testuser"
        }
        
        response = client.post("/auth/signup", json=incomplete_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_empty_password(self, client):
        invalid_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": ""
        }
        
        response = client.post("/auth/signup", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserLogin:
    def test_signin_success(self, client, test_user_credentials, session):
        create_user(test_user_credentials, session)
        
        login_data = {
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        }
        response = client.post("/auth/signin", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_credentials["email"]
        assert data["user"]["username"] == test_user_credentials["username"]

    def test_signin_wrong_password(self, client, test_user_credentials, session):

        create_user(test_user_credentials, session)
        
        login_data = {
            "email": test_user_credentials["email"],
            "password": "wrongpassword"
        }
        response = client.post("/auth/signin", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect email or password"

    def test_signin_nonexistent_user(self, client):
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        response = client.post("/auth/signin", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect email or password"

    def test_signin_invalid_email_format(self, client):
        login_data = {
            "email": "invalid-email",
            "password": "password123"
        }
        response = client.post("/auth/signin", json=login_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signin_missing_fields(self, client):
        incomplete_data = {
            "email": "test@example.com"
        }
        response = client.post("/auth/signin", json=incomplete_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserProfile:
    def test_get_profile_success(self, client, test_user_credentials, session):

        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        response = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user_credentials["email"]
        assert data["username"] == test_user_credentials["username"]
        assert data["role"] == "USER"

    def test_get_profile_no_token(self, client):
        response = client.get("/auth/profile")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_profile_invalid_token(self, client):
        response = client.get("/auth/profile", headers={
            "Authorization": "Bearer invalid_token"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_profile_malformed_header(self, client):
        response = client.get("/auth/profile", headers={
            "Authorization": "InvalidHeader"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAdminOperations:
    def test_get_all_users_admin_success(self, client, admin_user_credentials, session):

        admin_data = admin_user_credentials.copy()
        admin_data["role"] = "ADMIN"
        create_user(admin_data, session)

        user_data = {
            "username": "regularuser",
            "email": "regular@example.com",
            "password": "password123",
            "role": "USER"
        }
        create_user(user_data, session)
        
        login_response = client.post("/auth/signin", json={
            "email": admin_user_credentials["email"],
            "password": admin_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        
        response = client.get("/auth/get_all_users", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == status.HTTP_200_OK
        users = response.json()
        assert len(users) == 2
        assert any(user["role"] == "ADMIN" for user in users)
        assert any(user["role"] == "USER" for user in users)

    def test_get_all_users_regular_user_forbidden(self, client, test_user_credentials, session):

        create_user(test_user_credentials, session)
        

        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        
        response = client.get("/auth/get_all_users", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Admin access required"

    def test_get_all_users_no_token(self, client):
        response = client.get("/auth/get_all_users")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthenticationFlow:
    def test_complete_auth_flow(self, client, test_user_credentials):

        signup_response = client.post("/auth/signup", json=test_user_credentials)
        assert signup_response.status_code == status.HTTP_200_OK
        

        login_data = {
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        }
        signin_response = client.post("/auth/signin", json=login_data)
        assert signin_response.status_code == status.HTTP_200_OK
        
        token = signin_response.json()["access_token"]
        user_id = signin_response.json()["user"]["id"]
        

        profile_response = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token}"
        })
        assert profile_response.status_code == status.HTTP_200_OK
        assert profile_response.json()["id"] == user_id

    def test_multiple_users_isolation(self, client):

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
        

        client.post("/auth/signup", json=user1_data)
        client.post("/auth/signup", json=user2_data)
        

        login1_response = client.post("/auth/signin", json={
            "email": user1_data["email"],
            "password": user1_data["password"]
        })
        token1 = login1_response.json()["access_token"]
        

        login2_response = client.post("/auth/signin", json={
            "email": user2_data["email"],
            "password": user2_data["password"]
        })
        token2 = login2_response.json()["access_token"]
        

        assert token1 != token2
        

        profile1 = client.get("/auth/profile", headers={"Authorization": f"Bearer {token1}"})
        profile2 = client.get("/auth/profile", headers={"Authorization": f"Bearer {token2}"})
        
        assert profile1.json()["email"] == user1_data["email"]
        assert profile2.json()["email"] == user2_data["email"]
        assert profile1.json()["id"] != profile2.json()["id"]