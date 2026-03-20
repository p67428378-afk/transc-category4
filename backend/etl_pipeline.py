import pandas as pd
from sqlalchemy.orm import Session
from . import crud, schemas
from datetime import datetime

def clean_transaction_data(df: pd.DataFrame) -> pd.DataFrame:
    # Basic cleaning: strip whitespace from string columns
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].str.strip()
    return df

def deduplicate_transactions(df: pd.DataFrame) -> pd.DataFrame:
    # Deduplicate based on a combination of Date, Description, Amount
    # Assuming these columns exist and are relevant for uniqueness
    df_deduplicated = df.drop_duplicates(subset=['Date', 'Description', 'Amount'])
    return df_deduplicated

def categorize_transaction_llm_placeholder(description: str) -> str:
    # Placeholder for LLM categorization
    # In a real scenario, this would call an LLM API
    description_lower = description.lower()
    if "starbucks" in description_lower or "coffee" in description_lower:
        return "Food & Drink"
    elif "rent" in description_lower or "landlord" in description_lower:
        return "Housing"
    elif "utility" in description_lower or "con edison" in description_lower:
        return "Utilities"
    elif "salary" in description_lower or "paycheck" in description_lower:
        return "Income"
    else:
        return "Uncategorized"

def process_transactions_etl(db: Session, user_id: int, upload_batch_id: int, csv_file_path: str):
    # Read CSV
    df = pd.read_csv(csv_file_path)

    # Clean data
    df = clean_transaction_data(df)

    # Deduplicate
    df = deduplicate_transactions(df)

    # Categorize
    df['Category'] = df['Description'].apply(categorize_transaction_llm_placeholder)

    # Store in DB
    for index, row in df.iterrows():
        category_name = row['Category']
        category = crud.get_category_by_name(db, name=category_name)
        if not category:
            category = crud.create_category(db, schemas.CategoryCreate(name=category_name))

        transaction_data = schemas.TransactionCreate(
            date=datetime.strptime(row['Date'], '%Y-%m-%d'), # Assuming YYYY-MM-DD format
            description=row['Description'],
            amount=float(row['Amount']),
            raw_description=row['Description'], # Store original description
            category_id=category.id,
            status="CATEGORIZED"
        )
        crud.create_transaction(db, transaction=transaction_data, user_id=user_id, upload_batch_id=upload_batch_id)

    # Update upload batch status
    db_upload_batch = db.query(crud.models.UploadBatch).filter(crud.models.UploadBatch.id == upload_batch_id).first()
    if db_upload_batch:
        db_upload_batch.status = "COMPLETED"
        db.commit()
        db.refresh(db_upload_batch)
