from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional

class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    nickname: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nickname: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_rate: Optional[int] = None

class UserInDB(UserBase):
    id: int
    is_active: bool = True
    is_admin: bool = False
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    nickname: str
    is_active: bool
    is_admin: bool
    created_at: int
    last_login: Optional[int] = None
    tts_voice: str
    tts_rate: int
    model_config = ConfigDict(from_attributes=True)

class UserListResponse(BaseModel):
    total: int
    items: List[UserResponse]

class UserStatusUpdate(BaseModel):
    is_active: bool

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str