import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Groq Settings
    groq_api_key: str
    groq_model: str = "llama3-70b-8192"
    
    # Spotify Settings
    spotify_client_id: str
    spotify_client_secret: str
    
    # Google Maps Settings
    google_maps_api_key: str
    
    # Foursquare Settings
    foursquare_api_key: Optional[str] = None
    
    # GOAPI Settings - untuk pencarian tempat di Indonesia
    goapi_key: Optional[str] = None
    
    # Giphy Settings
    giphy_api_key: str
    
    # TMDb Settings
    tmdb_api_key: str
    
    # Application Settings
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    
    # CORS Settings
    frontend_url: str = "http://localhost:8080"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = "config/.env"
        case_sensitive = False

# Global settings instance
settings = Settings()
