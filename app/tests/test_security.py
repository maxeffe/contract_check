import pytest
from fastapi import status
import jwt
from datetime import datetime, timedelta
from services.crud.user import create_user


class TestJWTSecurity:
    def test_jwt_token_structure(self, client, test_user_credentials, session):
        """Тест структуры JWT токена"""
        
        create_user(test_user_credentials, session)
        
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        
        token = login_response.json()["access_token"]
        

        try:
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            

            assert "user_id" in decoded_token
            assert "email" in decoded_token
            assert "exp" in decoded_token  
            
            assert decoded_token["email"] == test_user_credentials["email"]
            
        except jwt.DecodeError:
            pytest.fail("JWT token has invalid structure")

    def test_token_expiration(self, client, test_user_credentials, session):
        """Тест истечения срока действия токена"""
        
        create_user(test_user_credentials, session)
        

        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token = login_response.json()["access_token"]
        

        decoded_token = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded_token["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        

        now = datetime.now()
        assert exp_datetime > now
        assert exp_datetime < now + timedelta(hours=1) 

    def test_invalid_token_formats(self, client):
        """Тест различных неправильных форматов токенов"""
        
        invalid_tokens = [
            "invalid_token",
            "Bearer",
            "",
            "Bearer ",
            "Bearer invalid.token.format",
            "NotBearer valid_looking_token",
            "Bearer " + "a" * 500, 
        ]
        
        for invalid_token in invalid_tokens:
            response = client.get("/auth/profile", headers={
                "Authorization": invalid_token
            })
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_reuse_security(self, client, test_user_credentials, session):
        """Тест безопасности повторного использования токенов"""
        
        create_user(test_user_credentials, session)
        

        login_response1 = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token1 = login_response1.json()["access_token"]
        

        login_response2 = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        token2 = login_response2.json()["access_token"]
        

        assert token1 != token2
        

        response1 = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token1}"
        })
        response2 = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token2}"
        })
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

    def test_token_tampering(self, client, test_user_credentials, session):
        """Тест защиты от изменения токена"""
        
        create_user(test_user_credentials, session)
        
  
        login_response = client.post("/auth/signin", json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        })
        original_token = login_response.json()["access_token"]
        

        parts = original_token.split('.')
        if len(parts) == 3:

            tampered_signature = parts[2][:-1] + 'X'
            tampered_token = f"{parts[0]}.{parts[1]}.{tampered_signature}"
            
            response = client.get("/auth/profile", headers={
                "Authorization": f"Bearer {tampered_token}"
            })
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cross_user_token_access(self, client, session):
        """Тест изоляции токенов между пользователями"""
        

        user1_data = {
            "username": "security_user1",
            "email": "security1@example.com",
            "password": "password123"
        }
        user2_data = {
            "username": "security_user2",
            "email": "security2@example.com",
            "password": "password123"
        }
        
        create_user(user1_data, session)
        create_user(user2_data, session)
        

        login1 = client.post("/auth/signin", json={
            "email": user1_data["email"],
            "password": user1_data["password"]
        })
        token1 = login1.json()["access_token"]
        user1_id = login1.json()["user"]["id"]
        
        login2 = client.post("/auth/signin", json={
            "email": user2_data["email"],
            "password": user2_data["password"]
        })
        token2 = login2.json()["access_token"]
        user2_id = login2.json()["user"]["id"]
        

        profile1 = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token1}"
        })
        profile2 = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token2}"
        })
        
        assert profile1.json()["id"] == user1_id
        assert profile2.json()["id"] == user2_id
        assert profile1.json()["email"] == user1_data["email"]
        assert profile2.json()["email"] == user2_data["email"]
        

        wallet1 = client.get("/wallet/balance", headers={
            "Authorization": f"Bearer {token1}"
        })
        wallet2 = client.get("/wallet/balance", headers={
            "Authorization": f"Bearer {token2}"
        })
        
        assert wallet1.status_code == status.HTTP_200_OK
        assert wallet2.status_code == status.HTTP_200_OK

        assert wallet1.json()["balance"] == "0"
        assert wallet2.json()["balance"] == "0"


class TestPasswordSecurity:
    def test_password_hashing(self, session):
        """Тест хеширования паролей"""
        
        user_data = {
            "username": "hash_test_user",
            "email": "hash@example.com",
            "password": "plaintext_password"
        }
        
        user = create_user(user_data, session)
        

        assert user.password != "plaintext_password"
        

        assert user.password.startswith("$2b$")
        assert len(user.password) > 50  

    def test_password_verification(self, session):
        """Тест проверки паролей"""
        
        user_data = {
            "username": "verify_test_user",
            "email": "verify@example.com",
            "password": "test_password_123"
        }
        
        user = create_user(user_data, session)
        

        assert user.verify_password("test_password_123") is True
        

        assert user.verify_password("wrong_password") is False
        assert user.verify_password("") is False
        assert user.verify_password("test_password_124") is False  
        assert user.verify_password("TEST_PASSWORD_123") is False  

    def test_different_users_different_hashes(self, session):
        """Тест что одинаковые пароли у разных пользователей дают разные хеши"""
        
        same_password = "identical_password"
        
        user1_data = {
            "username": "user1_hash",
            "email": "user1hash@example.com",
            "password": same_password
        }
        user2_data = {
            "username": "user2_hash",
            "email": "user2hash@example.com",
            "password": same_password
        }
        
        user1 = create_user(user1_data, session)
        user2 = create_user(user2_data, session)
        

        assert user1.password != user2.password
        

        assert user1.verify_password(same_password) is True
        assert user2.verify_password(same_password) is True


class TestInputValidation:
    def test_sql_injection_protection(self, client, session):
        """Тест защиты от SQL-инъекций"""
        

        malicious_inputs = [
            "'; DROP TABLE user; --",
            "admin' OR '1'='1",
            "admin'; UPDATE user SET role='ADMIN' WHERE id=1; --",
            "' UNION SELECT * FROM user --",
            "admin'/**/OR/**/1=1--",
        ]
        
        for malicious_input in malicious_inputs:

            response = client.post("/auth/signup", json={
                "username": "test_user",
                "email": malicious_input,
                "password": "password123"
            })
            

            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST
            ]
            

            response = client.post("/auth/signup", json={
                "username": malicious_input,
                "email": "test@example.com",
                "password": "password123"
            })
            

            response = client.post("/auth/signin", json={
                "email": malicious_input,
                "password": "password123"
            })

    def test_xss_protection(self, client, test_user_credentials, session):
        """Тест защиты от XSS атак"""
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
        ]
        
        for payload in xss_payloads:

            malicious_user_data = {
                "username": payload,
                "email": "xss@example.com",
                "password": "password123"
            }
            
            response = client.post("/auth/signup", json=malicious_user_data)
            
            if response.status_code == status.HTTP_200_OK:

                user_info = response.json()
   
                assert "<script>" not in user_info.get("user", {}).get("username", "")

    def test_rate_limiting_simulation(self, client):
        """Симуляция тестирования ограничения частоты запросов"""
        

        failed_attempts = 0
        max_attempts = 20
        
        for i in range(max_attempts):
            response = client.post("/auth/signin", json={
                "email": "nonexistent@example.com",
                "password": "wrong_password"
            })
            
            if response.status_code == status.HTTP_401_UNAUTHORIZED:
                failed_attempts += 1
            elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
        

        assert failed_attempts > 0 

    def test_large_payload_handling(self, client):
        """Тест обработки больших данных"""
        

        very_long_string = "a" * 10000
        
        response = client.post("/auth/signup", json={
            "username": very_long_string,
            "email": "long@example.com",
            "password": "password123"
        })
        

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        ]

    def test_special_characters_handling(self, client, session):
        """Тест обработки специальных символов"""
        
        special_chars_data = {
            "username": "user_тест_测试_🚀",
            "email": "special@example.com",
            "password": "pass_тест_测试_🔒"
        }
        
        response = client.post("/auth/signup", json=special_chars_data)
        
        if response.status_code == status.HTTP_200_OK:
            user_info = response.json()
            assert "тест" in user_info["user"]["username"]
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY