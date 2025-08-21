import pytest
from decimal import Decimal
from models.user import User
from services.crud.user import (
    create_user, 
    get_user_by_id, 
    get_user_by_email,
    get_user_by_username,
    get_all_users,
    authenticate_user,
    update_user,
    delete_user,
    user_exists_by_email,
    user_exists_by_username,
    count_users,
    get_users_by_role
)


class TestUserCreation:
    def test_create_user_success(self, session, sample_user_data_raw):
        original_password = sample_user_data_raw["password"]
        user = create_user(sample_user_data_raw, session)
        
        assert user.id is not None
        assert user.username == sample_user_data_raw["username"]
        assert user.email == sample_user_data_raw["email"]
        assert user.role == "USER"
        assert user.password != original_password 

    def test_create_admin_user(self, session, sample_admin_data):
        user = create_user(sample_admin_data, session)
        
        assert user.role == "ADMIN"
        assert user.username == sample_admin_data["username"]

    def test_password_hashing(self, session, sample_user_data_raw):
        original_password = sample_user_data_raw["password"]
        user = create_user(sample_user_data_raw, session)
        
        assert user.verify_password(original_password) is True
        assert user.verify_password("wrongpassword") is False


class TestUserRetrieval:
    def test_get_user_by_id(self, session, sample_user_data):
        created_user = create_user(sample_user_data, session)
        retrieved_user = get_user_by_id(created_user.id, session)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == created_user.username

    def test_get_user_by_email(self, session, sample_user_data):
        created_user = create_user(sample_user_data, session)
        retrieved_user = get_user_by_email(created_user.email, session)
        
        assert retrieved_user is not None
        assert retrieved_user.email == created_user.email

    def test_get_user_by_username(self, session, sample_user_data):
        created_user = create_user(sample_user_data, session)
        retrieved_user = get_user_by_username(created_user.username, session)
        
        assert retrieved_user is not None
        assert retrieved_user.username == created_user.username

    def test_get_nonexistent_user(self, session):
        user = get_user_by_id(999, session)
        assert user is None
        
        user = get_user_by_email("nonexistent@example.com", session)
        assert user is None


class TestUserAuthentication:
    def test_authenticate_valid_user(self, session, sample_user_data_raw):
        original_password = sample_user_data_raw["password"]
        create_user(sample_user_data_raw, session)
        
        authenticated_user = authenticate_user(
            sample_user_data_raw["email"], 
            original_password, 
            session
        )
        
        assert authenticated_user is not None
        assert authenticated_user.email == sample_user_data_raw["email"]

    def test_authenticate_invalid_password(self, session, sample_user_data):
        create_user(sample_user_data, session)
        
        authenticated_user = authenticate_user(
            sample_user_data["email"], 
            "wrongpassword", 
            session
        )
        
        assert authenticated_user is None

    def test_authenticate_nonexistent_user(self, session):
        authenticated_user = authenticate_user(
            "nonexistent@example.com", 
            "password", 
            session
        )
        
        assert authenticated_user is None


class TestUserUpdate:
    def test_update_user_username(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        
        updated_user = update_user(user.id, {"username": "newusername"}, session)
        
        assert updated_user.username == "newusername"
        assert updated_user.email == sample_user_data["email"]

    def test_update_user_password(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        new_password = "newpassword123"
        
        updated_user = update_user(user.id, {"password": new_password}, session)
        
        assert updated_user.verify_password(new_password) is True
        assert updated_user.verify_password(sample_user_data["password"]) is False

    def test_update_nonexistent_user(self, session):
        updated_user = update_user(999, {"username": "test"}, session)
        assert updated_user is None


class TestUserDeletion:
    def test_delete_user(self, session, sample_user_data):
        user = create_user(sample_user_data, session)
        user_id = user.id
        
        deleted = delete_user(user_id, session)
        assert deleted is True
        
        retrieved_user = get_user_by_id(user_id, session)
        assert retrieved_user is None

    def test_delete_nonexistent_user(self, session):
        deleted = delete_user(999, session)
        assert deleted is False


class TestUserUtilities:
    def test_user_exists_by_email(self, session, sample_user_data):
        assert user_exists_by_email(sample_user_data["email"], session) is False
        
        create_user(sample_user_data, session)
        assert user_exists_by_email(sample_user_data["email"], session) is True

    def test_user_exists_by_username(self, session, sample_user_data):
        assert user_exists_by_username(sample_user_data["username"], session) is False
        
        create_user(sample_user_data, session)
        assert user_exists_by_username(sample_user_data["username"], session) is True

    def test_count_users(self, session, sample_user_data, sample_admin_data):
        assert count_users(session) == 0
        
        create_user(sample_user_data, session)
        assert count_users(session) == 1
        
        create_user(sample_admin_data, session)
        assert count_users(session) == 2

    def test_get_users_by_role(self, session, sample_user_data, sample_admin_data):
        create_user(sample_user_data, session)
        create_user(sample_admin_data, session)
        
        users = get_users_by_role("USER", session)
        assert len(users) == 1
        assert users[0].role == "USER"
        
        admins = get_users_by_role("ADMIN", session)
        assert len(admins) == 1
        assert admins[0].role == "ADMIN"

    def test_get_all_users(self, session, sample_user_data, sample_admin_data):
        create_user(sample_user_data, session)
        create_user(sample_admin_data, session)
        
        all_users = get_all_users(session)
        assert len(all_users) == 2


class TestUserValidation:
    def test_invalid_email(self, session):
        pass

    def test_short_password(self, session):
        pass

    def test_user_validation_methods(self):
        """Тестируем валидаторы напрямую"""
        from models.user import User
        
        try:
            User.validate_email("invalid-email")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid email" in str(e)
        
        try:
            User.validate_password("123")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Password must be ≥ 8 chars" in str(e)
        
        assert User.validate_email("test@example.com") == "test@example.com"
        assert User.validate_password("password123") == "password123"