import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserRole = Literal["admin", "devops", "security"]


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = "devops"


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
