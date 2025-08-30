"""
Plan execution system for running planned tasks.
"""

import json
from datetime import datetime
from .models import Plan, PlanStep, StepStatus


class PlanExecutor:
    def __init__(self, agent):
        self.agent = agent
    
    def execute_step(self, step: PlanStep, state) -> str:
        step.status = StepStatus.IN_PROGRESS
        
        # IMPROVEMENT 2: Update progress recitation BEFORE executing step
        self._update_progress_recitation(step, state)
        
        # Build context for step execution
        context_info = ""
        if hasattr(state, 'files') and state.files:
            context_info = f"Available files: {', '.join(state.files.keys())}"
        
        step_prompt = f"""Execute this plan step:

ACTION: {step.action}
EXPECTED OUTPUT: {step.expected_output}
TOOLS NEEDED: {', '.join(step.tools_needed)}
CONTEXT: {context_info}

Execute this step using the available tools. Be thorough and methodical."""

        # Execute step with LLM
        messages = [
            {"role": "user", "content": step_prompt}
        ]
        
        response = self.agent.client.messages.create(
            model=self.agent.model,
            max_tokens=8000,
            system=self.agent.stable_system_prompt,  # CHANGED: Use stable prompt
            messages=messages,
            tools=self.agent.tool_registry.get_tool_schemas()
        )
 
        # Process response and tool calls
        step_result = self._process_step_response(response, state)
        step.actual_output = step_result
        step.status = StepStatus.COMPLETED
        
        # IMPROVEMENT 2: Use template variation to avoid few-shot ruts
        formatted_result = self._format_step_result(step, step_result)
        
        return formatted_result
    
    def _update_progress_recitation(self, current_step: PlanStep, state):
        """IMPROVEMENT 2: Keep objectives visible at end of context"""
        if hasattr(state, 'plan') and state.plan:
            plan_obj = Plan.from_dict(state.plan)
            
            # Create progress summary that appears at END of context
            completed_steps = [s for s in plan_obj.steps if s.status == StepStatus.COMPLETED]
            pending_steps = [s for s in plan_obj.steps if s.status == StepStatus.PENDING]
            
            progress_summary = f"""
=== CURRENT PROGRESS ===
OBJECTIVE: {plan_obj.objective}

COMPLETED ({len(completed_steps)} steps):
{chr(10).join([f"✅ {s.action}" for s in completed_steps])}

CURRENT TASK:
🔄 {current_step.action}

REMAINING ({len(pending_steps)-1} steps):
{chr(10).join([f"⏳ {s.action}" for s in pending_steps[1:]])}

=== END PROGRESS ===
"""
            
            # This gets read by agent in every subsequent call
            state.files["_current_progress.md"] = progress_summary
    
    def _format_step_result(self, step: PlanStep, result: str) -> str:
        """IMPROVEMENT 2: Add variation to avoid few-shot patterns"""
        template_idx = step.step_number % len(self.agent.response_templates)
        template = self.agent.response_templates[template_idx]
        
        # Truncate very long results for context, but keep full version in file
        display_result = result[:300] + "..." if len(result) > 300 else result
        
        return template.format(step=step.step_number, result=display_result)
    
    def _process_step_response(self, response, state) -> str:
        results = []
        
        for content_block in response.content:
            if hasattr(content_block, 'type'):
                if content_block.type == 'text':
                    results.append(content_block.text)
                elif content_block.type == 'tool_use':
                    try:
                        tool_result = self.agent.tool_registry.execute(
                            content_block.name,
                            content_block.input
                        )
                        # SUCCESS: Keep successful results
                        results.append(f"✅ [{content_block.name}] {tool_result}")
                        
                    except Exception as e:
                        # IMPROVEMENT 3: KEEP ERRORS IN CONTEXT (don't hide them)
                        error_context = f"""❌ [{content_block.name}] FAILED
Input: {content_block.input}
Error: {str(e)}
Note: This error is preserved for learning. Try different approach."""
                        
                        results.append(error_context)
                        
                        # ALSO save detailed error for later reference
                        error_file = f"error_step_{len(results)}.txt"
                        state.files[error_file] = f"""
Tool: {content_block.name}
Input: {json.dumps(content_block.input, indent=2)}
Error: {str(e)}
Timestamp: {datetime.now().isoformat()}
Context: This error occurred during step execution and should inform future decisions.
"""
        
        return "\n".join(results)