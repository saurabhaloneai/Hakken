"""
Tool-related data models.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable


@dataclass
class Tool:
    name: str
    description: str
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)