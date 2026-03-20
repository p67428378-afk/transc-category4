from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas, crud, dependencies, auth, services
from .database import create_db_and_tables
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

app = FastAPI()

# Create database tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(dependencies.get_db)):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(dependencies.get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(dependencies.get_current_user)):
    return current_user

@app.post("/api/transactions/upload", response_model=schemas.UploadBatch)
async def upload_transactions(
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    return await services.handle_transaction_upload(db, current_user.id, file)

@app.get("/api/transactions/report", response_model=List[schemas.Transaction])
async def get_transactions_report(
    current_user: schemas.User = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    return services.get_categorized_transactions_report(db, current_user.id)

@app.get("/api/categories/", response_model=List[schemas.Category])
async def get_all_categories(
    current_user: schemas.User = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    return crud.get_categories(db)
