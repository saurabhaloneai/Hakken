"""
Built-in tool implementations for the DeepAgent system.
"""

import os
import json
from typing import Optional
from .models import Tool


def create_builtin_tools(agent_instance):
    """Create built-in tools that need access to agent state."""
    
    def write_file(filename: str, content: str) -> str:
        agent_instance._current_state.files[filename] = content
        return f"✓ {filename} written ({len(content)} chars)"
    
    def save_to_disk(filename: str, content: str = None, folder: str = "deep_research_out") -> str:
        """Save file to disk in organized folder structure"""
        # Use content from internal files if not provided
        if content is None:
            content = agent_instance._current_state.files.get(filename, "")
            if not content:
                return f"❌ File {filename} not found in memory"
        
        # Determine subfolder based on filename
        if filename.startswith('final_') or filename.endswith('_report.md') or filename == 'final_output.md':
            subfolder = 'reports'
        elif filename.startswith('step_'):
            subfolder = 'steps'
        elif filename.startswith('plan') or filename.endswith('plan.json'):
            subfolder = 'plans'
        else:
            subfolder = 'sources'
        
        # Create full path
        full_folder = os.path.join(folder, subfolder)
        os.makedirs(full_folder, exist_ok=True)
        
        # Clean filename for disk
        clean_filename = filename.replace('_compressed_', '').replace('_current_progress', 'current_progress')
        filepath = os.path.join(full_folder, clean_filename)
        
        # Write to disk
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✓ {filepath} saved ({len(content)} chars)"
        except Exception as e:
            return f"❌ Failed to save {filepath}: {str(e)}"
    
    def read_file(filename: str) -> str:
        return agent_instance._current_state.files.get(filename, f"File {filename} not found")
    
    def ls() -> str:
        files = list(agent_instance._current_state.files.keys())
        return f"Files: {', '.join(files) if files else 'No files'}"
    
    def plan_task(objective: str, context: str = "") -> str:
        plan = agent_instance.planner.create_plan(objective, context)
        agent_instance._current_state.plan = plan.to_dict()
        return f"Plan created with {len(plan.steps)} steps: {', '.join([s.action for s in plan.steps])}"
    
    def call_subagent(subagent_name: str, task: str, context: str = "{}") -> str:
        try:
            context_dict = json.loads(context) if context != "{}" else {}
        except:
            context_dict = {"raw_context": context}
        
        return agent_instance.subagent_manager.call_subagent(subagent_name, task, context_dict)
    
    # Return list of built-in tools
    return [
        Tool("plan_task", "Create detailed plan", plan_task,
             {"objective": {"type": "string"}, "context": {"type": "string"}}, 
             ["objective"]),
        Tool("write_file", "Write file", write_file,
             {"filename": {"type": "string"}, "content": {"type": "string"}}, 
             ["filename", "content"]),
        Tool("save_to_disk", "Save file to disk in organized folders", save_to_disk,
             {"filename": {"type": "string"}, "content": {"type": "string"}, "folder": {"type": "string"}}, 
             ["filename"]),
        Tool("read_file", "Read file", read_file,
             {"filename": {"type": "string"}}, 
             ["filename"]),
        Tool("ls", "List files", ls, {}, []),
        Tool("call_subagent", "Delegate task to specialized sub-agent", call_subagent,
             {"subagent_name": {"type": "string"}, "task": {"type": "string"}, "context": {"type": "string"}}, 
             ["subagent_name", "task"])
    ]