from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIClientConfig(BaseSettings):
    api_key: str = Field(..., description="OpenAI API key")
    base_url: str = Field(..., description="OpenAI API base URL")
    model: str = Field(..., description="Model to use for completions")
    timeout: float = Field(120.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retry attempts")
    base_delay: float = Field(1.0, description="Base delay for exponential backoff")
    max_delay: float = Field(30.0, description="Maximum delay between retries")
    
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
