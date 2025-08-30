"""
Planning-related data models and enums.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class StepStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PlanStep:
    step_number: int
    action: str
    tools_needed: List[str]
    expected_output: str
    status: StepStatus = StepStatus.PENDING
    actual_output: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step_number,
            "action": self.action,
            "tools": self.tools_needed,
            "expected": self.expected_output,
            "status": self.status.value,
            "output": self.actual_output
        }


@dataclass
class Plan:
    objective: str
    steps: List[PlanStep]
    current_step_index: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "objective": self.objective,
            "steps": [step.to_dict() for step in self.steps],
            "current_step": self.current_step_index
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Plan':
        steps = []
        for step_data in data.get("steps", []):
            step = PlanStep(
                step_number=step_data["step"],
                action=step_data["action"],
                tools_needed=step_data.get("tools", []),
                expected_output=step_data.get("expected", ""),
                status=StepStatus(step_data.get("status", "pending"))
            )
            if "output" in step_data:
                step.actual_output = step_data["output"]
            steps.append(step)
        
        return cls(
            objective=data["objective"],
            steps=steps,
            current_step_index=data.get("current_step", 0)
        )
    
    def get_current_step(self) -> Optional[PlanStep]:
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def advance_step(self):
        if self.current_step_index < len(self.steps):
            self.current_step_index += 1
    
    def is_complete(self) -> bool:
        return self.current_step_index >= len(self.steps)