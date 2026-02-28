from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRE_MINUTES: int = 60
    OPENAI_API_KEY: str
    TAVILY_API_KEY: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

settings = Settings()