from pydantic import BaseModel, Field
from typing import Optional, Any, Dict


class ToolInput(BaseModel):
    class Config:
        extra = "forbid"
        validate_assignment = True


class ToolOutput(BaseModel):
    success: bool = Field(..., description="Whether the tool executed successfully")
    message: str = Field(..., description="Human-readable result message")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional structured data")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    
    class Config:
        validate_assignment = True
