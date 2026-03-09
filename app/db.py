import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/viridien")


def get_connection():
    return psycopg2.connect(DATABASE_URL)
