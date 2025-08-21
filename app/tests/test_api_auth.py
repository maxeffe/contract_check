import pytest
from fastapi import status

class TestUserRegistration:
    """Test user registration endpoints"""

    def test_signup_success(self, client, sample_user_data):
        """Test successful user registration"""
        response = client.post("/auth/signup", json=sample_user_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "User was created successfully"
        assert "user" in data
        assert data["user"]["email"] == sample_user_data["email"]
        assert data["user"]["username"] == sample_user_data["username"]
        assert data["user"]["role"] == "USER"

    def test_signup_duplicate_email(self, client, sample_user_data):
        """Test registration with duplicate email"""
        # First registration
        client.post("/auth/signup", json=sample_user_data)
        
        # Second registration with same email
        response = client.post("/auth/signup", json=sample_user_data)
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "User already exists"

    def test_signup_invalid_email(self, client):
        """Test registration with invalid email"""
        user_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        }
        
        response = client.post("/auth/signup", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_short_password(self, client):
        """Test registration with short password"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"
        }
        
        response = client.post("/auth/signup", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_missing_fields(self, client):
        """Test registration with missing required fields"""
        response = client.post("/auth/signup", json={
            "username": "testuser"
            # missing email and password
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserLogin:
    """Test user login endpoints"""

    def test_signin_success(self, client, test_user):
        """Test successful user login"""
        response = client.post("/auth/signin", json={
            "email": test_user.email,
            "password": "password123"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == test_user.email
        assert data["user"]["id"] == test_user.id

    def test_signin_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post("/auth/signin", json={
            "email": test_user.email,
            "password": "wrong_password"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect email or password"

    def test_signin_nonexistent_user(self, client):
        """Test login with nonexistent user"""
        response = client.post("/auth/signin", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect email or password"

    def test_signin_invalid_email_format(self, client):
        """Test login with invalid email format"""
        response = client.post("/auth/signin", json={
            "email": "invalid-email",
            "password": "password123"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserProfile:
    """Test user profile endpoints"""

    def test_get_profile_success(self, client, auth_headers, test_user):
        """Test successful profile retrieval"""
        response = client.get("/auth/profile", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert data["id"] == test_user.id

    def test_get_profile_no_token(self, client):
        """Test profile retrieval without token"""
        response = client.get("/auth/profile")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_profile_invalid_token(self, client):
        """Test profile retrieval with invalid token"""
        response = client.get("/auth/profile", headers={
            "Authorization": "Bearer invalid_token"
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAdminOperations:
    """Test admin-only operations"""

    def test_get_all_users_admin_success(self, client, admin_headers):
        """Test admin can get all users"""
        response = client.get("/auth/get_all_users", headers=admin_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_all_users_regular_user_forbidden(self, client, auth_headers):
        """Test regular user cannot get all users"""
        response = client.get("/auth/get_all_users", headers=auth_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Admin access required"

    def test_get_all_users_no_token(self, client):
        """Test get all users without authentication"""
        response = client.get("/auth/get_all_users")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthenticationFlow:
    """Test complete authentication flows"""

    def test_complete_auth_flow(self, client):
        """Test complete registration -> login -> profile flow"""
        # Registration
        user_data = {
            "username": "flowtest",
            "email": "flowtest@example.com",
            "password": "password123"
        }
        
        signup_response = client.post("/auth/signup", json=user_data)
        assert signup_response.status_code == status.HTTP_200_OK
        
        # Login
        login_response = client.post("/auth/signin", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        
        # Get Profile
        profile_response = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token}"
        })
        assert profile_response.status_code == status.HTTP_200_OK
        profile_data = profile_response.json()
        assert profile_data["email"] == user_data["email"]
        assert profile_data["username"] == user_data["username"]

    def test_multiple_users_isolation(self, client):
        """Test that users are properly isolated"""
        # Create two users
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
        
        # Register both users
        client.post("/auth/signup", json=user1_data)
        client.post("/auth/signup", json=user2_data)
        
        # Login both users
        login1 = client.post("/auth/signin", json={
            "email": user1_data["email"],
            "password": user1_data["password"]
        })
        
        login2 = client.post("/auth/signin", json={
            "email": user2_data["email"],
            "password": user2_data["password"]
        })
        
        token1 = login1.json()["access_token"]
        token2 = login2.json()["access_token"]
        
        # Verify profiles are different
        profile1 = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token1}"
        })
        
        profile2 = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token2}"
        })
        
        assert profile1.json()["email"] == user1_data["email"]
        assert profile2.json()["email"] == user2_data["email"]
        assert profile1.json()["id"] != profile2.json()["id"]


class TestAuthenticationValidation:
    """Test authentication validation and edge cases"""

    def test_expired_token_handling(self, client):
        """Test handling of expired tokens (simulated)"""
        # This would require mocking time or using a very short expiration
        # For now, we test with an obviously invalid token
        response = client.get("/auth/profile", headers={
            "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired"
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_malformed_authorization_header(self, client):
        """Test malformed authorization headers"""
        # Missing Bearer prefix
        response = client.get("/auth/profile", headers={
            "Authorization": "some_token"
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Empty header
        response = client.get("/auth/profile", headers={
            "Authorization": ""
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_case_sensitivity_email(self, client):
        """Test email case sensitivity in login"""
        # Register with lowercase email
        user_data = {
            "username": "casetest",
            "email": "casetest@example.com",
            "password": "password123"
        }
        client.post("/auth/signup", json=user_data)
        
        # Try to login with uppercase email
        response = client.post("/auth/signin", json={
            "email": "CASETEST@EXAMPLE.COM",
            "password": "password123"
        })
        
        # This should fail as emails should be case sensitive
        assert response.status_code == status.HTTP_401_UNAUTHORIZED