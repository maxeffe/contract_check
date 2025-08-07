from fastapi import APIRouter, HTTPException, status, Depends
from models.user import User
from services.crud import user as UserService
from database.database import get_session
from schemas.auth import UserRegistrationRequest, UserLoginRequest, TokenResponse, UserResponse, AuthResponse
from auth.jwt_handler import create_access_token, get_current_user
from datetime import timedelta
from config.logging_config import auth_logger

user_route = APIRouter(tags=['User'])

@user_route.post("/signup")
async def signup(data: UserRegistrationRequest, session=Depends(get_session)) -> AuthResponse:
    auth_logger.info(f"Попытка регистрации пользователя: {data.email}")
    
    if UserService.get_user_by_email(data.email, session) is not None:
        auth_logger.warning(f"Попытка регистрации существующего пользователя: {data.email}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='User already exists')
    
    user_data = {
        "username": data.username,
        "email": data.email,
        "password": data.password
    }
    created_user = UserService.create_user(user_data, session)
    auth_logger.info(f"Пользователь успешно зарегистрирован: {created_user.email} (ID: {created_user.id})")
    
    user_response = UserResponse(
        id=created_user.id,
        username=created_user.username,
        email=created_user.email,
        role=created_user.role
    )
    
    return AuthResponse(message="User was created successfully", user=user_response)


@user_route.post("/signin")
async def signin(data: UserLoginRequest, session=Depends(get_session)) -> TokenResponse:
    auth_logger.info(f"Попытка входа пользователя: {data.email}")
    
    user = UserService.authenticate_user(data.email, data.password, session)
    if user is None:
        auth_logger.warning(f"Неудачная попытка входа: {data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email}, 
        expires_delta=access_token_expires
    )
    
    auth_logger.info(f"Пользователь успешно авторизован: {user.email} (ID: {user.id})")
    
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role
    )
    
    return TokenResponse(access_token=access_token, user=user_response)


@user_route.get('/profile')
async def get_profile(
    current_user=Depends(get_current_user),
    session=Depends(get_session)
) -> UserResponse:
    user = UserService.get_user_by_id(current_user["user_id"], session)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role
    )

@user_route.get('/get_all_users')
async def get_all_users(
    current_user=Depends(get_current_user),
    session=Depends(get_session)
):
    user = UserService.get_user_by_id(current_user["user_id"], session)
    if not user or user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    
    return UserService.get_all_users(session=session)
