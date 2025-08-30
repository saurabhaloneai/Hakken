"""
Planning system for creating task execution plans.
"""

import json
from .models import Plan, PlanStep


class Planner:
    def __init__(self, agent):
        self.agent = agent
    
    def needs_planning(self, task: str) -> bool:
        keywords = ["research", "analyze", "comprehensive", "detailed", "investigate", 
                   "compare", "evaluate", "create report", "study", "analyze"]
        
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in keywords) or len(task.split()) > 15
    
    def create_plan(self, objective: str, context: str = "") -> Plan:
        available_tools = list(self.agent.tool_registry.tools.keys())
        
        planning_prompt = f"""Create a detailed step-by-step plan for this objective: {objective}

Available context: {context}
Available tools: {', '.join(available_tools)}

Return ONLY a JSON object with this exact structure:
{{
    "objective": "{objective}",
    "steps": [
        {{
            "step": 1,
            "action": "Clear description of what to do",
            "tools": ["list", "of", "tool", "names"],
            "expected": "What this step should produce"
        }},
        {{
            "step": 2,
            "action": "Next action description", 
            "tools": ["tool", "names"],
            "expected": "Expected output"
        }}
    ]
}}

Make steps specific and actionable. Each step should build toward the final objective."""

        try:
            # Use higher max_tokens for Sonnet 4, lower for older models
            max_tokens = 8000 if "sonnet-4" in self.agent.model else 4000
            response = self.agent.client.messages.create(
                model=self.agent.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": planning_prompt}]
            )
            
            plan_text = response.content[0].text
            # Extract JSON from response
            start_idx = plan_text.find('{')
            end_idx = plan_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                plan_json = plan_text[start_idx:end_idx]
                plan_data = json.loads(plan_json)
                return Plan.from_dict(plan_data)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Plan parsing error: {e}")
        
        # Fallback plan
        return Plan(
            objective=objective,
            steps=[
                PlanStep(1, f"Begin work on: {objective}", ["write_file"], "Initial analysis"),
                PlanStep(2, "Process and analyze information", ["write_file"], "Analysis results"),
                PlanStep(3, "Create comprehensive final output", ["write_file"], "Final deliverable")
            ]
        )