import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Configuration
    polymarket_api_key: Optional[str] = os.getenv("POLYMARKET_API_KEY")
    polymarket_secret: Optional[str] = os.getenv("POLYMARKET_SECRET") 
    polymarket_passphrase: Optional[str] = os.getenv("POLYMARKET_PASSPHRASE")
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///../data/polymarket_ai.db")
    
    # Server
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "3000"))
    
    # Trading
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    max_position_size: float = float(os.getenv("MAX_POSITION_SIZE", "100.0"))
    risk_tolerance: float = float(os.getenv("RISK_TOLERANCE", "0.25"))
    enable_auto_trading: bool = os.getenv("ENABLE_AUTO_TRADING", "false").lower() == "true"
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def has_polymarket_api(self) -> bool:
        return all([
            self.polymarket_api_key,
            self.polymarket_secret,
            self.polymarket_passphrase
        ])
    
    @property
    def has_google_api(self) -> bool:
        return bool(self.google_api_key)
    
    class Config:
        env_file = ".env"

settings = Settings()