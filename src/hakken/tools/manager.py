from typing import Dict, Any, List, Optional, TYPE_CHECKING

from hakken.tools.base import BaseTool

if TYPE_CHECKING:
    from hakken.terminal_bridge import UIManager
    from hakken.history.manager import HistoryManager
    from hakken.subagents.manager import SubagentManager


TOOL_REGISTRY = {
    "cmd_runner": ("hakken.tools.execution.terminal", "CmdRunner"),
    "read_file": ("hakken.tools.filesystem.read", "ReadFileTool"),
    "edit_file": ("hakken.tools.filesystem.edit", "EditFileTool"),
    "search_replace": ("hakken.tools.filesystem.search_replace", "SearchReplaceTool"),
    "delete_file": ("hakken.tools.filesystem.delete", "DeleteFileTool"),
    "list_dir": ("hakken.tools.filesystem.list_dir", "ListDirTool"),
    "add_memory": ("hakken.tools.memory.add", "AddMemoryTool"),
    "list_memories": ("hakken.tools.memory.list", "ListMemoriesTool"),
    "semantic_search": ("hakken.tools.search.semantic_search", "SemanticSearchTool"),
    "file_search": ("hakken.tools.search.file_search", "FileSearchTool"),
    "grep_search": ("hakken.tools.search.grep_search", "GrepSearchTool"),
    "git_status": ("hakken.tools.git.status", "GitStatusTool"),
    "git_diff": ("hakken.tools.git.diff", "GitDiffTool"),
    "git_commit": ("hakken.tools.git.commit", "GitCommitTool"),
    "git_push": ("hakken.tools.git.push", "GitPushTool"),
    "git_log": ("hakken.tools.git.log", "GitLogTool"),
    "context_compression": ("hakken.tools.utilities.context_compression", "ContextCompressionTool"),
    "todo_write": ("hakken.tools.utilities.todo", "TodoTool"),
    "task": ("hakken.tools.utilities.task", "TaskTool"),
    "scratchpad": ("hakken.tools.utilities.scratchpad", "ScratchpadTool"),
}


class ToolManager:
    
    def __init__(
        self, 
        history_manager: Optional["HistoryManager"] = None, 
        ui_manager: Optional["UIManager"] = None, 
        subagent_manager: Optional["SubagentManager"] = None
    ):
        self.tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, type] = {}
        self.history_manager = history_manager
        self.ui_manager = ui_manager
        self.subagent_manager = subagent_manager
        self._tools_initialized = False

    def _ensure_tools_loaded(self):
        if self._tools_initialized:
            return
        self._tools_initialized = True
        
        for name, (module_path, class_name) in TOOL_REGISTRY.items():
            if name == "context_compression" and not self.history_manager:
                continue
            if name == "todo_write" and not self.ui_manager:
                continue
            if name == "task" and not (self.subagent_manager and self.ui_manager):
                continue
            
            try:
                import importlib
                module = importlib.import_module(module_path)
                tool_class = getattr(module, class_name)
                
                if name == "context_compression":
                    self.tools[name] = tool_class(history_manager=self.history_manager)
                elif name == "todo_write":
                    self.tools[name] = tool_class(ui_manager=self.ui_manager)
                elif name == "task":
                    self.tools[name] = tool_class(
                        subagent_manager=self.subagent_manager,
                        ui_manager=self.ui_manager
                    )
                elif name == "scratchpad":
                    self.tools[name] = tool_class(ui_manager=self.ui_manager)
                else:
                    self.tools[name] = tool_class()
            except Exception:
                pass

    def register_tool(self, tool: BaseTool):
        self.tools[tool.get_tool_name()] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        self._ensure_tools_loaded()
        return self.tools.get(name)

    def get_tools_description(self) -> List[Dict[str, Any]]:
        self._ensure_tools_loaded()
        return [tool.json_schema() for tool in self.tools.values()]

    def get_tool_status(self, tool_name: str) -> str:
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Tool '{tool_name}' not found."
        if hasattr(tool, 'get_status'):
            return tool.get_status()
        return f"Tool '{tool_name}' does not have a status."

    async def run_tool(self, tool_name: str, **kwargs) -> Any:
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found."
        
        return await tool.act(**kwargs)