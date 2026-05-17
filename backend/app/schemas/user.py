import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Use the same enum as the DB models to keep role values in sync
from app.db.models import UserRole as DBUserRole

# Pydantic will accept Enum values; using the DB enum prevents mismatches
UserRole = DBUserRole


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = DBUserRole.DEVOPS


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
