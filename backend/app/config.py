from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENV: str = "development"
    PORT: int = 8000
    GEMINI_API_KEY: str
    
    # Dual-Database Connection Targets
    PRIMARY_DB_URL: str
    REPLICA_DB_URL: str

    # Direct Pydantic to inspect the local .env file inside backend/
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()