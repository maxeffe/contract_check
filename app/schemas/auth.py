from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegistrationRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class AuthResponse(BaseModel):
    message: str
    user: Optional[UserResponse] = None