from models.user import User
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import List, Optional


def get_all_users(session: Session) -> List[User]:
    """Получить всех пользователей"""
    statement = select(User)
    result = session.exec(statement)
    return list(result.all())


def get_user_by_id(user_id: int, session: Session) -> Optional[User]:
    """Получить пользователя по ID"""
    statement = select(User).where(User.id == user_id)
    result = session.exec(statement)
    return result.first()


def get_user_by_email(email: str, session: Session) -> Optional[User]:
    """Получить пользователя по email"""
    statement = select(User).where(User.email == email)
    result = session.exec(statement)
    return result.first()


def get_user_by_username(username: str, session: Session) -> Optional[User]:
    """Получить пользователя по username"""
    statement = select(User).where(User.username == username)
    result = session.exec(statement)
    return result.first()


def create_user(user_data: dict, session: Session) -> User:
    """Создать нового пользователя"""
    if 'password' in user_data:
        user_data['password'] = User.hash_password(user_data['password'])
    
    user = User(**user_data)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user(user_id: int, user_data: dict, session: Session) -> Optional[User]:
    """Обновить данные пользователя"""
    user = get_user_by_id(user_id, session)
    if not user:
        return None
    
    if 'password' in user_data:
        user_data['password'] = User.hash_password(user_data['password'])
    
    for key, value in user_data.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def delete_user(user_id: int, session: Session) -> bool:
    """Удалить пользователя по ID"""
    user = get_user_by_id(user_id, session)
    if not user:
        return False
    
    session.delete(user)
    session.commit()
    return True


def authenticate_user(email: str, password: str, session: Session) -> Optional[User]:
    """Аутентификация пользователя по email и паролю"""
    user = get_user_by_email(email, session)
    if not user:
        return None
    
    if user.verify_password(password):
        return user
    return None


def get_users_by_role(role: str, session: Session) -> List[User]:
    """Получить пользователей по роли"""
    statement = select(User).where(User.role == role)
    result = session.exec(statement)
    return list(result.all())


def user_exists_by_email(email: str, session: Session) -> bool:
    """Проверить существование пользователя по email"""
    user = get_user_by_email(email, session)
    return user is not None


def user_exists_by_username(username: str, session: Session) -> bool:
    """Проверить существование пользователя по username"""
    user = get_user_by_username(username, session)
    return user is not None


def count_users(session: Session) -> int:
    """Подсчитать общее количество пользователей"""
    statement = select(User)
    result = session.exec(statement)
    return len(list(result.all()))