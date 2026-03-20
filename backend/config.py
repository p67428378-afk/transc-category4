import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
DATABASE_URL = os.getenv("DATABASE_URL")

if not all([SECRET_KEY, ALGORITHM, DATABASE_URL]):
    raise ValueError("Missing one or more environment variables: SECRET_KEY, ALGORITHM, DATABASE_URL")
