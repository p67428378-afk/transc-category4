from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from .config import DATABASE_URL

# Use a default in-memory SQLite for testing if DATABASE_URL is not set
# This is a temporary measure for initial development and testing
# In a real application, you'd want a more robust testing setup
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./test.db"
    print("WARNING: DATABASE_URL not set, using in-memory SQLite for development.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    transactions = relationship("Transaction", back_populates="owner")
    upload_batches = relationship("UploadBatch", back_populates="owner")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    transactions = relationship("Transaction", back_populates="category")

class UploadBatch(Base):
    __tablename__ = "upload_batches"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    file_name = Column(String)
    status = Column(String, default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED

    owner = relationship("User", back_populates="upload_batches")
    transactions = relationship("Transaction", back_populates="upload_batch")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    upload_batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=True)
    date = Column(DateTime)
    description = Column(String)
    amount = Column(Float)
    raw_description = Column(String, nullable=True) # Original description before cleaning
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    status = Column(String, default="UNCATEGORIZED") # UNCATEGORIZED, CATEGORIZED, PENDING_LLM

    owner = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    upload_batch = relationship("UploadBatch", back_populates="transactions")

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
