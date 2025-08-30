"""
SubAgent-related data models.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SubAgentConfig:
    name: str
    description: str
    prompt: str
    tools: Optional[List[str]] = None