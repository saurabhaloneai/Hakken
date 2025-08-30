"""
Main DeepAgent class and core functionality.
"""

import json
import inspect
from typing import Dict, List, Any, Optional, Callable

import anthropic

from ..planning.planner import Planner
from ..planning.executor import PlanExecutor
from ..planning.models import Plan, StepStatus
from ..tools.registry import ToolRegistry
from ..tools.models import Tool
from ..tools.builtin_tools import create_builtin_tools
from ..subagents.manager import SubAgentManager
from ..subagents.models import SubAgentConfig
from .models import EnhancedAgentState, Message
from .utils import manage_context_memory, compress_large_outputs


class DeepAgent:
    def __init__(self, tools: List[Callable] = None, instructions: str = "",
                 subagents: List[Dict] = None, api_key: str = None, 
                 model: str = "claude-sonnet-4-20250514"):
        
        # Core components
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.instructions = instructions
        self.tool_registry = ToolRegistry()
        
        # Planning components  
        self.planner = Planner(self)
        self.executor = PlanExecutor(self)
       
        # IMPROVEMENT 2: Template variations for avoiding few-shot ruts
        self.response_templates = [
            "Step {step} completed: {result}",
            "Action {step} executed: {result}", 
            "Task {step} finished: {result}",
            "Operation {step} done: {result}",
            "Phase {step} accomplished: {result}",
            "Process {step} concluded: {result}"
        ]
        
        # Sub-agent system
        self.subagent_manager = SubAgentManager(self)
        
        # IMPROVEMENT 1: Build stable system prompt (never changes - KV-cache optimization)
        self.stable_system_prompt = self._build_stable_system_prompt()
        
        # Register custom sub-agents
        if subagents:
            for sa_config in subagents:
                self.subagent_manager.register_subagent(sa_config)
        
        # Register tools
        self._register_builtin_tools()
        if tools:
            self._register_tools(tools)
        
        # Keep legacy system_prompt for compatibility
        self.system_prompt = self.stable_system_prompt
        
    def _build_stable_system_prompt(self) -> str:
        """IMPROVEMENT 1: Build the stable part of system prompt (for KV-cache)"""
        subagent_list = self.subagent_manager.get_subagent_descriptions()
        
        # This part NEVER changes - perfect for caching
        stable_prompt = f"""You are an advanced AI agent with planning and delegation capabilities.

CORE CAPABILITIES:
- Complex task planning and execution
- Tool integration for external operations
- Sub-agent delegation for specialized work
- File system for persistent context
- Comprehensive analysis and processing

AVAILABLE SUB-AGENTS:
{subagent_list}

WORKFLOW:
1. Analyze task complexity and requirements
2. Create plan for multi-step tasks (use plan_task)  
3. Execute steps directly or delegate to specialized sub-agents
4. Maintain context through file system
5. Synthesize final comprehensive results

ERROR HANDLING PRINCIPLE: When tools fail or return errors, keep the error information in context. This helps you learn and avoid repeating mistakes.

{self.instructions}"""
                
        return stable_prompt
    
    def _register_builtin_tools(self):
        builtin_tools = create_builtin_tools(self)
        for tool in builtin_tools:
            self.tool_registry.register(tool)
    
    def _register_tools(self, tools):
        for tool_func in tools:
            sig = inspect.signature(tool_func)
            params = {}
            for param_name, param in sig.parameters.items():
                params[param_name] = {"type": "string"}
            
            tool = Tool(
                name=tool_func.__name__,
                description=tool_func.__doc__ or f"Execute {tool_func.__name__}",
                function=tool_func,
                parameters=params
            )
            self.tool_registry.register(tool)
    
    def invoke(self, input_data: Dict) -> Dict:
        messages = input_data.get("messages", [])
        files = input_data.get("files", {})
        
        # Enhanced state with sub-agent support
        state = EnhancedAgentState(
            messages=[Message(**msg) for msg in messages],
            files=files.copy()
        )
        self._current_state = state
        
        user_task = messages[-1]["content"] if messages else ""
        
        # IMPROVEMENT 7: Manage context memory before planning
        manage_context_memory(state)
        
        # Planning phase
        if self.planner.needs_planning(user_task) and not state.plan:
            plan = self.planner.create_plan(user_task, str(state.files))
            state.plan = plan.to_dict()
            
            plan_msg = f"Created {len(plan.steps)}-step plan:\n"
            for i, step in enumerate(plan.steps, 1):
                plan_msg += f"{i}. {step.action}\n"
            plan_msg += "\nExecuting systematically..."
            
            state.messages.append(Message(role="assistant", content=plan_msg))
            state.files["plan.json"] = json.dumps(state.plan, indent=2)
        
        # Execution phase
        if state.plan:
            self._execute_plan_with_subagents(state)
        else:
            self._execute_with_delegation(state, user_task)
        
        return {
            "messages": [{"role": msg.role, "content": msg.content} for msg in state.messages],
            "files": state.files
        }
    
    def _execute_plan_with_subagents(self, state):
        plan = Plan.from_dict(state.plan)
        
        for step_num, step in enumerate(plan.steps, 1):
            if step.status != StepStatus.PENDING:
                continue
            
            # Determine if step should be delegated
            subagent_name = self._choose_subagent_for_step(step)
            
            if subagent_name:
                # Delegate to sub-agent
                context = {
                    "plan_objective": plan.objective,
                    "step_number": step_num,
                    "previous_outputs": [s.actual_output for s in plan.steps[:step_num-1] if s.actual_output],
                    "available_files": list(state.files.keys())
                }
                
                step_result = self.subagent_manager.call_subagent(
                    subagent_name, 
                    step.action, 
                    context
                )
                
                delegation_msg = f"Step {step_num} → Delegated to {subagent_name}\n{step_result[:200]}..."
                state.messages.append(Message(role="assistant", content=delegation_msg))
            else:
                # Execute directly
                step_result = self.executor.execute_step(step, state)
                direct_msg = f"Step {step_num} executed directly\n{step_result[:200]}..."
                state.messages.append(Message(role="assistant", content=direct_msg))
            
            # Update step status
            step.actual_output = step_result
            step.status = StepStatus.COMPLETED
            state.files[f"step_{step_num}_output.txt"] = step_result
            
            # Update plan in state
            state.plan = plan.to_dict()
            
            # IMPROVEMENT 4: Compress large outputs if needed
            compress_large_outputs(state)
        
        # Plan execution completed - just notify
        state.messages.append(Message(role="assistant", content="Plan execution completed. Check output files for results."))
    
    def _execute_with_delegation(self, state, task):
        # For simple tasks, determine if delegation would help
        if self._should_delegate_simple_task(task):
            subagent_name = self._choose_subagent_for_task(task)
            if subagent_name and subagent_name in self.subagent_manager.subagents:
                result = self.subagent_manager.call_subagent(subagent_name, task)
                state.messages.append(Message(role="assistant", content=result))
            else:
                # Execute directly if no suitable sub-agent
                response = self._get_llm_response(state)
                result = self._process_response_with_tools(response, state)
                state.messages.append(Message(role="assistant", content=result))
        else:
            # Execute directly
            response = self._get_llm_response(state)
            result = self._process_response_with_tools(response, state)
            state.messages.append(Message(role="assistant", content=result))
    
    def _choose_subagent_for_step(self, step) -> Optional[str]:
        action_lower = step.action.lower()
        
        # Try to match step actions with available sub-agents
        for subagent_name, subagent in self.subagent_manager.subagents.items():
            desc_lower = subagent.description.lower()
            if any(word in action_lower for word in ["analyze", "process"] if "analysis" in desc_lower):
                return subagent_name
            elif any(word in action_lower for word in ["write", "report", "document"] if "report" in desc_lower or "writing" in desc_lower):
                return subagent_name
            elif any(word in action_lower for word in ["research", "gather", "find"] if "research" in desc_lower):
                return subagent_name
        
        return None  # Execute directly
    
    def _choose_subagent_for_task(self, task: str) -> Optional[str]:
        task_lower = task.lower()
        
        # Try to match tasks with available sub-agents
        for subagent_name, subagent in self.subagent_manager.subagents.items():
            desc_lower = subagent.description.lower()
            if any(word in task_lower for word in ["analyze", "compare", "evaluate"] if "analysis" in desc_lower):
                return subagent_name
            elif any(word in task_lower for word in ["write report", "document", "summarize"] if "report" in desc_lower or "writing" in desc_lower):
                return subagent_name
        
        return None
    
    def _should_delegate_simple_task(self, task: str) -> bool:
        delegation_keywords = ["analyze", "write report", "compare", "process", "evaluate"]
        return any(keyword in task.lower() for keyword in delegation_keywords)
    
    def _get_llm_response(self, state):
        # IMPROVEMENT 5: Build context with KV-cache optimization
        messages = self._build_optimized_context(state)
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=self.stable_system_prompt,  # CHANGED: Use stable prompt
            messages=messages,
            tools=self.tool_registry.get_tool_schemas()
        )
        
        return response
    
    def _build_optimized_context(self, state) -> List[Dict]:
        """IMPROVEMENT 5: Build context optimized for KV-cache"""
        messages = []
        
        # Add conversation history (stable part)
        for msg in state.messages:
            messages.append({"role": msg.role, "content": msg.content})
        
        # IMPROVEMENT 2: Add current progress recitation at the END
        if "_current_progress.md" in state.files:
            progress_content = state.files["_current_progress.md"]
            messages.append({
                "role": "user", 
                "content": f"CURRENT CONTEXT:\n{progress_content}"
            })
        
        return messages
    
    def _process_response_with_tools(self, response, state) -> str:
        results = []
        
        for content_block in response.content:
            if hasattr(content_block, 'type'):
                if content_block.type == 'text':
                    results.append(content_block.text)
                elif content_block.type == 'tool_use':
                    try:
                        tool_result = self.tool_registry.execute(
                            content_block.name,
                            content_block.input
                        )
                        results.append(f"✅ [{content_block.name}] {tool_result}")
                    except Exception as e:
                        # IMPROVEMENT 3: Keep errors in context
                        error_msg = f"❌ [{content_block.name}] FAILED: {str(e)}"
                        results.append(error_msg)
        
        return "\n".join(results)