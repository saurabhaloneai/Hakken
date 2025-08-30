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
        """Write file to memory and automatically save to disk"""
        agent_instance._current_state.files[filename] = content
        
        # Auto-save to disk with error handling
        try:
            disk_result = save_to_disk(filename, content)
            return f"✓ {filename} written ({len(content)} chars) & saved to disk"
        except Exception as e:
            return f"✓ {filename} written ({len(content)} chars) but disk save failed: {str(e)}"
    
    def save_to_disk(filename: str, content: str = None, folder: str = "deep_research_out") -> str:
        """Save file to disk in organized folder structure"""
        # Use content from internal files if not provided
        if content is None:
            content = agent_instance._current_state.files.get(filename, "")
            if not content:
                return f"⚠ File {filename} not found in memory"
        
        # Skip compressed files and internal progress files
        if filename.startswith('_compressed_') or filename.startswith('_current_'):
            return f"⚠ Skipped internal file: {filename}"
        
        # Determine subfolder based on filename
        if filename.startswith('final_') or filename.endswith('_report.md') or filename == 'final_output.md':
            subfolder = 'reports'
        elif filename.startswith('step_'):
            subfolder = 'steps'
        elif filename.startswith('plan') or filename.endswith('plan.json'):
            subfolder = 'plans'
        elif filename.startswith('error_'):
            subfolder = 'errors'
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
            return f"⚠ Failed to save {filepath}: {str(e)}"
    
    def save_all_files(folder: str = "deep_research_out") -> str:
        """Save all files from memory to disk in organized structure"""
        saved_count = 0
        failed_count = 0
        results = []
        
        for filename, content in agent_instance._current_state.files.items():
            # Skip internal compressed and progress files
            if filename.startswith('_compressed_') or filename.startswith('_current_'):
                continue
                
            try:
                save_result = save_to_disk(filename, content, folder)
                if "✓" in save_result:
                    saved_count += 1
                else:
                    failed_count += 1
                    results.append(save_result)
            except Exception as e:
                failed_count += 1
                results.append(f"⚠ Failed to save {filename}: {str(e)}")
        
        summary = f"✓ Saved {saved_count} files to {folder}"
        if failed_count > 0:
            summary += f", {failed_count} failed"
            
        if results:
            summary += f"\nIssues:\n" + "\n".join(results)
            
        return summary
    
    def read_file(filename: str) -> str:
        """Read file from memory"""
        return agent_instance._current_state.files.get(filename, f"File {filename} not found")
    
    def ls() -> str:
        """List all files in memory"""
        files = list(agent_instance._current_state.files.keys())
        if not files:
            return "No files in memory"
            
        # Organize file listing
        regular_files = [f for f in files if not f.startswith('_')]
        internal_files = [f for f in files if f.startswith('_')]
        
        result = f"Files ({len(regular_files)} regular, {len(internal_files)} internal):\n"
        
        if regular_files:
            result += "Regular files:\n" + "\n".join(f"  • {f}" for f in regular_files)
        
        if internal_files:
            result += f"\nInternal files:\n" + "\n".join(f"  • {f}" for f in internal_files)
            
        return result
    
    def plan_task(objective: str, context: str = "") -> str:
        """Create detailed execution plan for complex tasks"""
        plan = agent_instance.planner.create_plan(objective, context)
        agent_instance._current_state.plan = plan.to_dict()
        
        # Auto-save plan to disk
        plan_content = json.dumps(plan.to_dict(), indent=2)
        agent_instance._current_state.files["plan.json"] = plan_content
        
        try:
            save_to_disk("plan.json", plan_content)
            save_status = "& saved to disk"
        except Exception as e:
            save_status = f"but disk save failed: {str(e)}"
        
        return f"Plan created with {len(plan.steps)} steps {save_status}: {', '.join([s.action for s in plan.steps])}"
    
    def call_subagent(subagent_name: str, task: str, context: str = "{}") -> str:
        """Delegate task to specialized sub-agent"""
        try:
            context_dict = json.loads(context) if context != "{}" else {}
        except:
            context_dict = {"raw_context": context}
        
        return agent_instance.subagent_manager.call_subagent(subagent_name, task, context_dict)
    
    def clear_memory() -> str:
        """Clear all files from memory (useful for fresh starts)"""
        file_count = len(agent_instance._current_state.files)
        agent_instance._current_state.files.clear()
        return f"✓ Cleared {file_count} files from memory"
    
    def get_disk_status(folder: str = "deep_research_out") -> str:
        """Check what files exist on disk vs memory"""
        memory_files = set(agent_instance._current_state.files.keys())
        memory_files = {f for f in memory_files if not f.startswith('_')}  # Skip internal files
        
        disk_files = set()
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), folder)
                    # Convert back to simple filename for comparison
                    simple_name = os.path.basename(file)
                    disk_files.add(simple_name)
        
        in_memory_only = memory_files - disk_files
        on_disk_only = disk_files - memory_files
        synced = memory_files & disk_files
        
        result = f"📊 File Status:\n"
        result += f"  • Synced (memory + disk): {len(synced)} files\n"
        result += f"  • Memory only: {len(in_memory_only)} files\n"
        result += f"  • Disk only: {len(on_disk_only)} files\n"
        
        if in_memory_only:
            result += f"\nMemory only files: {', '.join(sorted(in_memory_only))}"
        if on_disk_only:
            result += f"\nDisk only files: {', '.join(sorted(on_disk_only))}"
            
        return result
    
    # Return list of built-in tools
    return [
        Tool("plan_task", "Create detailed plan for complex tasks", plan_task,
             {"objective": {"type": "string"}, "context": {"type": "string"}}, 
             ["objective"]),
        Tool("write_file", "Write file to memory and auto-save to disk", write_file,
             {"filename": {"type": "string"}, "content": {"type": "string"}}, 
             ["filename", "content"]),
        Tool("save_to_disk", "Manually save specific file to disk in organized folders", save_to_disk,
             {"filename": {"type": "string"}, "content": {"type": "string"}, "folder": {"type": "string"}}, 
             ["filename"]),
        Tool("save_all_files", "Save all files from memory to disk", save_all_files,
             {"folder": {"type": "string"}}, 
             []),
        Tool("read_file", "Read file from memory", read_file,
             {"filename": {"type": "string"}}, 
             ["filename"]),
        Tool("ls", "List all files in memory with organization", ls, {}, []),
        Tool("call_subagent", "Delegate task to specialized sub-agent", call_subagent,
             {"subagent_name": {"type": "string"}, "task": {"type": "string"}, "context": {"type": "string"}}, 
             ["subagent_name", "task"]),
        Tool("clear_memory", "Clear all files from memory", clear_memory, {}, []),
        Tool("get_disk_status", "Check file synchronization between memory and disk", get_disk_status,
             {"folder": {"type": "string"}}, 
             [])
    ]