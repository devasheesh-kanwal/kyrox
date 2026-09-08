import os
from dotenv import load_dotenv

# .env file se keys load karo
load_dotenv()

class Config:
    # OpenTopography Config
    OPEN_TOPOGRAPHY_KEY = os.getenv("OPEN_TOPOGRAPHY_KEY")
    OPEN_TOPOGRAPHY_URL = os.getenv("OPEN_TOPOGRAPHY_URL")
    
    # Validation: Agar key nahi mili toh error do
    @staticmethod
    def validate():
        if not Config.OPEN_TOPOGRAPHY_KEY:
            raise ValueError("OPEN_TOPOGRAPHY_KEY missing in .env file!")
        if not Config.OPEN_TOPOGRAPHY_URL:
            raise ValueError("OPEN_TOPOGRAPHY_URL missing in .env file!")