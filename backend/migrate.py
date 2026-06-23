# backend/migrate.py
import os
from dotenv import load_dotenv
from yoyo import read_migrations, get_backend

def run_database_migrations():
    load_dotenv()
    
    # 1. Grab your primary database connection string
    db_url = os.environ.get("PRIMARY_DB_URL")
    if not db_url:
        raise ValueError("PRIMARY_DB_URL is missing from your .env file!")
        
    print(f"Connecting to Primary Database inside Docker...")
    
    # 2. Initialize yoyo backend and read your migrations directory
    backend = get_backend(db_url)
    migrations = read_migrations('./migrations')
    
    # 3. Apply all unapplied migrations safely
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
    
    print("🚀 Database migrations successfully applied to Primary node!")

if __name__ == "__main__":
    run_database_migrations()