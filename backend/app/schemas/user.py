from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    role: str = "viewer"


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
