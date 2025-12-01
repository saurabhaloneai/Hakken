"""Base Pydantic schemas for tool inputs and outputs."""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict


class ToolInput(BaseModel):
    """Base class for all tool inputs.
    
    All tool input models should inherit from this class.
    Prevents unexpected fields from being accepted.
    """
    
    class Config:
        extra = "forbid"  # Reject any fields not defined in the model
        validate_assignment = True  # Validate on attribute assignment


class ToolOutput(BaseModel):
    """Base class for all tool outputs.
    
    Provides a consistent structure for tool execution results.
    """
    success: bool = Field(..., description="Whether the tool executed successfully")
    message: str = Field(..., description="Human-readable result message")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional structured data")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    
    class Config:
        validate_assignment = True
