from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    # Add other fields you want to expose, but NOT password

class Token(BaseModel):
    access_token: str
    token_type: str