from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    date: datetime
    description: str
    amount: float

class TransactionCreate(TransactionBase):
    raw_description: Optional[str] = None
    category_id: Optional[int] = None
    status: Optional[str] = "UNCATEGORIZED"

class Transaction(TransactionBase):
    id: int
    user_id: int
    upload_batch_id: Optional[int] = None
    raw_description: Optional[str] = None
    category_id: Optional[int] = None
    status: str
    category: Optional[Category] = None

    class Config:
        from_attributes = True

class UploadBatchBase(BaseModel):
    file_name: str

class UploadBatchCreate(UploadBatchBase):
    pass

class UploadBatch(UploadBatchBase):
    id: int
    user_id: int
    upload_timestamp: datetime
    status: str
    transactions: List[Transaction] = []

    class Config:
        from_attributes = True
