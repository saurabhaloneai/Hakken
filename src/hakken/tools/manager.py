from typing import Dict, Any, List, Optional, TYPE_CHECKING

from hakken.tools.base import BaseTool
from hakken.history.manager import HistoryManager

from hakken.tools.execution.terminal import CmdRunner
from hakken.tools.filesystem.read import ReadFileTool
from hakken.tools.filesystem.edit import EditFileTool
from hakken.tools.filesystem.search_replace import SearchReplaceTool
from hakken.tools.filesystem.delete import DeleteFileTool
from hakken.tools.filesystem.list_dir import ListDirTool
from hakken.tools.memory.add import AddMemoryTool
from hakken.tools.memory.list import ListMemoriesTool
from hakken.tools.search.semantic_search import SemanticSearchTool
from hakken.tools.search.file_search import FileSearchTool
from hakken.tools.search.grep_search import GrepSearchTool
from hakken.tools.git.status import GitStatusTool
from hakken.tools.git.diff import GitDiffTool
from hakken.tools.git.commit import GitCommitTool
from hakken.tools.git.push import GitPushTool
from hakken.tools.git.log import GitLogTool
from hakken.tools.utilities.todo import TodoTool
from hakken.tools.utilities.task import TaskTool
from hakken.tools.utilities.context_compression import ContextCompressionTool

if TYPE_CHECKING:
    from hakken.terminal_bridge import UIManager

from hakken.subagents.manager import SubagentManager


class ToolManager:
    
    def __init__(
        self, 
        history_manager: Optional[HistoryManager] = None, 
        ui_manager: Optional["UIManager"] = None, 
        subagent_manager: Optional[SubagentManager] = None
    ):
        self.tools: Dict[str, BaseTool] = {}
        self.history_manager = history_manager
        self.ui_manager = ui_manager
        self.subagent_manager = subagent_manager
        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool(CmdRunner())
        
        self.register_tool(ReadFileTool())
        self.register_tool(EditFileTool())
        self.register_tool(SearchReplaceTool())
        self.register_tool(DeleteFileTool())
        self.register_tool(ListDirTool())
        
        self.register_tool(AddMemoryTool())
        self.register_tool(ListMemoriesTool())
        
        self.register_tool(SemanticSearchTool())
        self.register_tool(FileSearchTool())
        self.register_tool(GrepSearchTool())
        
 
        self.register_tool(GitStatusTool())
        self.register_tool(GitDiffTool())
        self.register_tool(GitCommitTool())
        self.register_tool(GitPushTool())
        self.register_tool(GitLogTool())
        
        if self.history_manager:
            self.register_tool(ContextCompressionTool(history_manager=self.history_manager))
        
        if self.ui_manager:
            self.register_tool(TodoTool(ui_manager=self.ui_manager))
            
        if self.subagent_manager and self.ui_manager:
            self.register_tool(TaskTool(
                subagent_manager=self.subagent_manager, 
                ui_manager=self.ui_manager
            ))

    def register_tool(self, tool: BaseTool):
        self.tools[tool.get_tool_name()] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)

    def get_tools_description(self) -> List[Dict[str, Any]]:
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