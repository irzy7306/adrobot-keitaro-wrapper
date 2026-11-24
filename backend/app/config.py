from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = 'postgresql+psycopg://adrobot:adrobot@db:5432/adrobot'
    keitaro_url: str = 'https://tlgk.host'
    keitaro_api_key: str = ''
    campaign_prefix: str = 'test_raznitsina_'
    cors_origins: str = 'http://localhost:5173'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

@lru_cache
def get_settings(): return Settings()
