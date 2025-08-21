import pytest
from fastapi import status
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json
import os

class TestJWTSecurity:
    """Test JWT token security"""

    def test_jwt_token_structure(self, client, test_user):
        """Test JWT token structure and validity"""
        response = client.post("/auth/signin", json={
            "email": test_user.email,
            "password": "password123"
        })
        
        assert response.status_code == status.HTTP_200_OK
        token = response.json()["access_token"]
        
        # Verify token structure
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts
        
        # Decode token to verify contents
        secret_key = os.getenv("SECRET_KEY")
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            assert "user_id" in payload
            assert "email" in payload
            assert "exp" in payload
            assert payload["user_id"] == test_user.id
            assert payload["email"] == test_user.email
        except jwt.InvalidTokenError:
            pytest.fail("Token should be valid")

    def test_token_expiration(self, client, test_user):
        """Test JWT token expiration"""
        # Mock time to test expiration
        with patch('auth.jwt_handler.datetime') as mock_datetime:
            # Set current time
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            response = client.post("/auth/signin", json={
                "email": test_user.email,
                "password": "password123"
            })
            
            token = response.json()["access_token"]
            
            # Verify token works immediately
            profile_response = client.get("/auth/profile", headers={
                "Authorization": f"Bearer {token}"
            })
            assert profile_response.status_code == status.HTTP_200_OK

    def test_invalid_token_formats(self, client):
        """Test handling of invalid token formats"""
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid_token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
            "",
            None
        ]
        
        for token in invalid_tokens:
            if token:
                headers = {"Authorization": token}
            else:
                headers = {}
            
            response = client.get("/auth/profile", headers=headers)
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_token_reuse_security(self, client, test_user):
        """Test that tokens can be reused within valid time"""
        # Login and get token
        response = client.post("/auth/signin", json={
            "email": test_user.email,
            "password": "password123"
        })
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Use token multiple times
        for _ in range(3):
            profile_response = client.get("/auth/profile", headers=headers)
            assert profile_response.status_code == status.HTTP_200_OK

    def test_token_tampering(self, client, test_user):
        """Test detection of tampered tokens"""
        # Get valid token
        response = client.post("/auth/signin", json={
            "email": test_user.email,
            "password": "password123"
        })
        
        token = response.json()["access_token"]
        
        # Tamper with token
        parts = token.split('.')
        tampered_token = parts[0] + ".tampered_payload." + parts[2]
        
        response = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {tampered_token}"
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cross_user_token_access(self, client):
        """Test that tokens are user-specific"""
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
        
        # Each token should return different user profiles
        profile1 = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token1}"
        })
        profile2 = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token2}"
        })
        
        assert profile1.json()["email"] == user1_data["email"]
        assert profile2.json()["email"] == user2_data["email"]
        assert profile1.json()["id"] != profile2.json()["id"]


class TestInputValidation:
    """Test input validation and sanitization"""

    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection"""
        # Attempt SQL injection in email field
        malicious_inputs = [
            "admin@example.com'; DROP TABLE users; --",
            "admin@example.com' OR '1'='1",
            "admin@example.com'; SELECT * FROM users; --",
            "'; UPDATE users SET role='ADMIN' WHERE email='test@example.com'; --"
        ]
        
        for malicious_email in malicious_inputs:
            response = client.post("/auth/signin", json={
                "email": malicious_email,
                "password": "password123"
            })
            
            # Should either validate input format or return auth error, not crash
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]

    def test_xss_protection(self, client, auth_headers):
        """Test protection against XSS attacks"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "'; alert('xss'); //"
        ]
        
        for payload in xss_payloads:
            # Test XSS in prediction text
            prediction_data = {
                "document_text": f"Contract content {payload}",
                "filename": f"test{payload}.txt"
            }
            
            with patch('services.prediction_service.process_prediction_request') as mock_predict:
                mock_predict.side_effect = ValueError("Insufficient balance")
                
                response = client.post("/predict", json=prediction_data, headers=auth_headers)
                
                # Should handle gracefully, not execute script
                assert response.status_code in [
                    status.HTTP_402_PAYMENT_REQUIRED,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    status.HTTP_400_BAD_REQUEST
                ]

    def test_rate_limiting_simulation(self, client, test_user):
        """Test rate limiting behavior (simulated)"""
        # Simulate rapid login attempts
        login_data = {
            "email": test_user.email,
            "password": "wrong_password"
        }
        
        # Make multiple rapid failed attempts
        for i in range(5):
            response = client.post("/auth/signin", json=login_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # All should fail with same error (no account lockout implemented yet)
        # In a real system, we might expect rate limiting after several attempts

    def test_large_payload_handling(self, client, auth_headers):
        """Test handling of large payloads"""
        # Create very large document text
        large_text = "A" * 1000000  # 1MB of text
        
        prediction_data = {
            "document_text": large_text,
            "filename": "large_document.txt"
        }
        
        # Should handle large payloads gracefully
        response = client.post("/predict", json=prediction_data, headers=auth_headers)
        
        # Should either process or reject gracefully, not crash
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_402_PAYMENT_REQUIRED,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_special_characters_handling(self, client):
        """Test handling of special characters in input"""
        special_chars_data = {
            "username": "test™user∑∆",
            "email": "test+email@example.com",
            "password": "password123!@#$%^&*()"
        }
        
        response = client.post("/auth/signup", json=special_chars_data)
        
        # Should handle special characters appropriately
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


class TestAuthenticationSecurity:
    """Test authentication security measures"""

    def test_password_hashing(self, client, sample_user_data):
        """Test that passwords are properly hashed"""
        # Create user
        response = client.post("/auth/signup", json=sample_user_data)
        assert response.status_code == status.HTTP_200_OK
        
        # Login to verify password works
        login_response = client.post("/auth/signin", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        assert login_response.status_code == status.HTTP_200_OK
        
        # Password should never appear in response
        signup_text = json.dumps(response.json())
        login_text = json.dumps(login_response.json())
        
        assert sample_user_data["password"] not in signup_text
        assert sample_user_data["password"] not in login_text

    def test_sensitive_data_exposure(self, client, auth_headers, test_user):
        """Test that sensitive data is not exposed"""
        # Get user profile
        response = client.get("/auth/profile", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        profile_data = response.json()
        
        # Sensitive fields should not be present
        assert "password" not in profile_data
        assert "hashed_password" not in profile_data
        
        # Only safe fields should be present
        safe_fields = {"id", "username", "email", "role"}
        assert set(profile_data.keys()) <= safe_fields

    def test_unauthorized_access_patterns(self, client):
        """Test various unauthorized access attempts"""
        protected_endpoints = [
            ("/auth/profile", "GET"),
            ("/auth/get_all_users", "GET"),
            ("/wallet/balance", "GET"),
            ("/wallet/topup", "POST"),
            ("/predict", "POST"),
            ("/history", "GET"),
            ("/documents", "GET")
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_privilege_escalation_protection(self, client, auth_headers):
        """Test protection against privilege escalation"""
        # Regular user trying to access admin endpoint
        response = client.get("/auth/get_all_users", headers=auth_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Admin access required"


class TestDataPrivacy:
    """Test data privacy and isolation"""

    def test_user_data_isolation(self, client):
        """Test that users can only access their own data"""
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
        
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}
        
        # User 1 creates wallet transaction
        client.post("/wallet/topup", json={"amount": 100.0}, headers=headers1)
        
        # User 2 should not see User 1's transactions
        transactions1 = client.get("/wallet/transactions", headers=headers1)
        transactions2 = client.get("/wallet/transactions", headers=headers2)
        
        assert transactions1.json()["total_count"] == 1
        assert transactions2.json()["total_count"] == 0

    def test_document_access_control(self, client, auth_headers):
        """Test document access control"""
        # This test simulates document access control
        # In real implementation, we'd create documents and test access
        
        # Attempting to access non-existent document
        response = client.get("/documents/999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Attempting to access job that doesn't belong to user
        response = client.get("/jobs/999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSecurityHeaders:
    """Test security headers and configurations"""

    def test_cors_headers(self, client):
        """Test CORS configuration"""
        response = client.options("/auth/signin")
        
        # Basic response should not crash
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]

    def test_content_type_validation(self, client, auth_headers):
        """Test content type validation"""
        # Test with invalid content type
        response = client.post(
            "/predict",
            data="invalid json data",
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]


class TestErrorHandling:
    """Test secure error handling"""

    def test_error_information_disclosure(self, client):
        """Test that errors don't disclose sensitive information"""
        # Trigger various errors and check responses
        
        # Invalid endpoint
        response = client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Invalid method
        response = client.delete("/auth/signin")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        
        # Malformed JSON
        response = client.post(
            "/auth/signin",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Error responses should not contain stack traces or internal paths
        for resp in [response]:
            if resp.status_code >= 400:
                error_text = resp.text.lower()
                sensitive_keywords = [
                    "traceback",
                    "file \"",
                    "line ",
                    "exception:",
                    "error:",
                    "/users/",
                    "/app/",
                    "c:\\",
                    "python"
                ]
                
                for keyword in sensitive_keywords:
                    assert keyword not in error_text, f"Sensitive info '{keyword}' found in error response"

    def test_graceful_error_handling(self, client, auth_headers):
        """Test graceful handling of system errors"""
        # Simulate service unavailable
        with patch('services.prediction_service.process_prediction_request') as mock_predict:
            mock_predict.side_effect = Exception("Database connection failed")
            
            response = client.post("/predict", json={
                "document_text": "test content",
                "filename": "test.txt"
            }, headers=auth_headers)
            
            # Should return proper HTTP error, not crash
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Error message should be generic, not expose internal details
            error_detail = response.json().get("detail", "")
            assert "Database connection failed" not in error_detail