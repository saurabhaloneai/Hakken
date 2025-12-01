from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

################ API Client Configuration ################

class APIClientConfig(BaseSettings):
    api_key: str = Field(...)
    base_url: str = Field(...)
    model: str = Field(...)
    timeout: float = Field(120.0)
    max_retries: int = Field(3)
    base_delay: float = Field(1.0)
    max_delay: float = Field(30.0)
    
    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v
    
    @field_validator('max_retries')
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        if v < 0:
            raise ValueError("max_retries must be non-negative")
        return v
    
    @field_validator('base_delay', 'max_delay')
    @classmethod
    def validate_delay(cls, v: float) -> float:
        if v < 0:
            raise ValueError("delay must be non-negative")
        return v
