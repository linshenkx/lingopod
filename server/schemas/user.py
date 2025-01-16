from typing import Optional, List
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    nickname: Optional[str] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None


class UserInDB(UserBase):
    id: int
    created_at: int
    last_login: Optional[int] = None

    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    pass


class UserListResponse(BaseModel):
    total: int
    items: List[UserResponse]


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str