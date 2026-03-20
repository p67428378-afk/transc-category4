import pandas as pd
from io import StringIO
from sqlalchemy.orm import Session
from . import crud, schemas, etl_pipeline
from fastapi import UploadFile, HTTPException, status
import os

async def handle_transaction_upload(db: Session, user_id: int, file: UploadFile):
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed."
        )

    # Create an upload batch record
    upload_batch = crud.create_upload_batch(db, user_id=user_id, file_name=file.filename)

    # Read CSV content
    contents = await file.read()
    s_io = StringIO(contents.decode('utf-8'))

    # Save to a temporary file for pandas to read (or directly use StringIO with pandas)
    # For simplicity, let's assume pandas can read from StringIO directly
    # In a real-world scenario, for large files, you might save to disk or object storage first.
    temp_csv_path = f"/tmp/{upload_batch.id}_{file.filename}"
    with open(temp_csv_path, "wb") as f:
        f.write(contents)

    try:
        etl_pipeline.process_transactions_etl(db, user_id, upload_batch.id, temp_csv_path)
    except Exception as e:
        # Update batch status to FAILED if ETL fails
        db_upload_batch = db.query(crud.models.UploadBatch).filter(crud.models.UploadBatch.id == upload_batch.id).first()
        if db_upload_batch:
            db_upload_batch.status = "FAILED"
            db.commit()
            db.refresh(db_upload_batch)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction processing failed: {e}"
        )
    finally:
        # Clean up temporary file
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)

    return upload_batch

def get_categorized_transactions_report(db: Session, user_id: int):
    transactions = crud.get_transactions(db, user_id=user_id)
    report_data = []
    for trans in transactions:
        report_data.append({
            "id": trans.id,
            "date": trans.date.isoformat(),
            "description": trans.description,
            "amount": trans.amount,
            "category": trans.category.name if trans.category else "Uncategorized",
            "status": trans.status
        })
    return report_data
