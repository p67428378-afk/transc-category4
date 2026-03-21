import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend import crud, schemas, auth
from datetime import datetime, timedelta
import io
import csv

# Helper function to create a user and get a token
def get_user_and_token(client: TestClient, email: str, password: str):
    # Register user
    response = client.post(
        "/users/",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text

    # Login and get token
    response = client.post(
        "/token",
        data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return token

def test_create_user(client: TestClient):
    response = client.post(
        "/users/",
        json={"email": "test@example.com", "password": "password"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

    # Try to register with existing email
    response = client.post(
        "/users/",
        json={"email": "test@example.com", "password": "password2"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_for_access_token(client: TestClient):
    # First, create a user
    client.post(
        "/users/",
        json={"email": "login@example.com", "password": "password"}
    )

    response = client.post(
        "/token",
        data={"username": "login@example.com", "password": "password"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Test with incorrect password
    response = client.post(
        "/token",
        data={"username": "login@example.com", "password": "wrong_password"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

    # Test with non-existent user
    response = client.post(
        "/token",
        data={"username": "nonexistent@example.com", "password": "password"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_read_users_me(client: TestClient):
    token = get_user_and_token(client, "me@example.com", "password")

    response = client.get(
        "/users/me/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "id" in data

    # Test with invalid token
    response = client.get(
        "/users/me/",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

def test_upload_transactions_success(client: TestClient, db_session: Session):
    token = get_user_and_token(client, "upload@example.com", "password")

    csv_content = """Date,Description,Amount
2023-01-01,Starbucks Coffee,5.50
2023-01-02,Whole Foods Market,75.20
2023-01-03,Monthly Rent,1200.00
2023-01-04,Electricity Bill,80.00
"""
    response = client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("transactions.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )
    assert response.status_code == 200, response.text
    upload_batch = response.json()
    assert upload_batch["file_name"] == "transactions.csv"
    assert upload_batch["status"] == "COMPLETED"
    assert "id" in upload_batch

    # Verify transactions are in the database
    user = crud.get_user_by_email(db_session, email="upload@example.com")
    transactions = crud.get_transactions(db_session, user_id=user.id)
    assert len(transactions) == 4

    # Check categorization for a few transactions
    starbucks_trans = next(t for t in transactions if "Starbucks" in t.description)
    assert starbucks_trans.category.name == "Food & Drink"
    assert starbucks_trans.status == "CATEGORIZED"

    whole_foods_trans = next(t for t in transactions if "Whole Foods" in t.description)
    assert whole_foods_trans.category.name == "Food & Drink" # Placeholder logic might categorize this as Food & Drink
    assert whole_foods_trans.status == "CATEGORIZED"

    rent_trans = next(t for t in transactions if "Rent" in t.description)
    assert rent_trans.category.name == "Housing"
    assert rent_trans.status == "CATEGORIZED"

    electricity_trans = next(t for t in transactions if "Electricity" in t.description)
    assert electricity_trans.category.name == "Utilities"
    assert electricity_trans.status == "CATEGORIZED"

def test_upload_transactions_invalid_file_type(client: TestClient):
    token = get_user_and_token(client, "invalidfile@example.com", "password")

    response = client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("document.txt", io.BytesIO(b"some text"), "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are allowed."

def test_upload_transactions_malformed_csv(client: TestClient, db_session: Session):
    token = get_user_and_token(client, "malformed@example.com", "password")

    csv_content = """Date,Description,Amount,ExtraColumn
2023-01-01,Starbucks Coffee,5.50,extra
InvalidDate,Description,Amount,extra
""" # Malformed date
    response = client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("malformed.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )
    assert response.status_code == 500 # Expecting internal server error due to parsing
    assert "Transaction processing failed" in response.json()["detail"]

    # Verify upload batch status is FAILED
    user = crud.get_user_by_email(db_session, email="malformed@example.com")
    upload_batches = db_session.query(crud.models.UploadBatch).filter(crud.models.UploadBatch.user_id == user.id).all()
    assert len(upload_batches) == 1
    assert upload_batches[0].status == "FAILED"

def test_upload_transactions_empty_csv(client: TestClient, db_session: Session):
    token = get_user_and_token(client, "emptycsv@example.com", "password")

    csv_content = """Date,Description,Amount
"""
    response = client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("empty.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )
    assert response.status_code == 200, response.text
    upload_batch = response.json()
    assert upload_batch["file_name"] == "empty.csv"
    assert upload_batch["status"] == "COMPLETED" # ETL should complete even if no rows processed

    # Verify no transactions are in the database
    user = crud.get_user_by_email(db_session, email="emptycsv@example.com")
    transactions = crud.get_transactions(db_session, user_id=user.id)
    assert len(transactions) == 0

def test_get_transactions_report_success(client: TestClient, db_session: Session):
    token = get_user_and_token(client, "report@example.com", "password")

    csv_content = """Date,Description,Amount
2023-02-01,Coffee Shop,4.00
2023-02-05,Grocery Store,50.00
"""
    client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("report.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )

    response = client.get(
        "/api/transactions/report",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert len(report) == 2
    assert report[0]["description"] == "Coffee Shop"
    assert report[0]["category"] == "Food & Drink"
    assert report[1]["description"] == "Grocery Store"
    assert report[1]["category"] == "Uncategorized" # Based on placeholder logic

def test_get_transactions_report_no_transactions(client: TestClient):
    token = get_user_and_token(client, "noreport@example.com", "password")

    response = client.get(
        "/api/transactions/report",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert len(report) == 0

def test_deduplication_in_etl(client: TestClient, db_session: Session):
    token = get_user_and_token(client, "dedupe@example.com", "password")

    csv_content = """Date,Description,Amount
2023-03-01,Duplicate Item,10.00
2023-03-01,Duplicate Item,10.00
2023-03-02,Unique Item,20.00
"""
    response = client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("dedupe.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )
    assert response.status_code == 200, response.text

    user = crud.get_user_by_email(db_session, email="dedupe@example.com")
    transactions = crud.get_transactions(db_session, user_id=user.id)
    assert len(transactions) == 2 # Only 2 unique transactions should be stored

    duplicate_item_count = sum(1 for t in transactions if "Duplicate Item" in t.description)
    assert duplicate_item_count == 1

def test_llm_placeholder_categorization(client: TestClient, db_session: Session):
    token = get_user_and_token(client, "llmtest@example.com", "password")

    csv_content = """Date,Description,Amount
2023-04-01,Starbucks,5.00
2023-04-02,My Landlord Payment,1500.00
2023-04-03,Con Edison Bill,120.00
2023-04-04,Random Shop,30.00
2023-04-05,Paycheck Deposit,2000.00
"""
    response = client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("llmtest.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )
    assert response.status_code == 200, response.text

    user = crud.get_user_by_email(db_session, email="llmtest@example.com")
    transactions = crud.get_transactions(db_session, user_id=user.id)

    starbucks_trans = next(t for t in transactions if "Starbucks" in t.description)
    assert starbucks_trans.category.name == "Food & Drink"

    landlord_trans = next(t for t in transactions if "Landlord" in t.description)
    assert landlord_trans.category.name == "Housing"

    con_edison_trans = next(t for t in transactions if "Con Edison" in t.description)
    assert con_edison_trans.category.name == "Utilities"

    random_shop_trans = next(t for t in transactions if "Random Shop" in t.description)
    assert random_shop_trans.category.name == "Uncategorized"

    paycheck_trans = next(t for t in transactions if "Paycheck" in t.description)
    assert paycheck_trans.category.name == "Income"

def test_get_all_categories(client: TestClient, db_session: Session):
    token = get_user_and_token(client, "categoryuser@example.com", "password")

    # Upload some transactions to create categories
    csv_content = """Date,Description,Amount
2023-05-01,Starbucks,5.00
2023-05-02,Rent Payment,1000.00
"""
    client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("categories.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )

    response = client.get(
        "/api/categories/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    categories = response.json()
    category_names = [c["name"] for c in categories]
    assert "Food & Drink" in category_names
    assert "Housing" in category_names
    assert "Uncategorized" in category_names # Default category
