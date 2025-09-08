from typing import Dict, List, Any
from .tool_interface import ToolInterface
from .command_runner import CommandRunner
from .context_cropper import ContextCropper
from .todo_writer import TodoWriteManager
from .task_delegator import TaskDelegator
from .task_memory_tool import TaskMemoryTool
from .file_reader import FileReader
from .grep_search import GrepSearch
from .git_tools import GitTools
from .file_editor import FileEditor
from .web_search import WebSearch


class ToolManager:

    def __init__(self, ui_interface=None, history_manager=None, conversation_agent=None):
        self.tools: Dict[str, ToolInterface] = {}
        # Important tools should be placed lower, as this affects their position in the prompt
        # Match existing tool names and constructors used elsewhere in the codebase
        self._register_tool(ContextCropper(history_manager))
        self._register_tool(TodoWriteManager(ui_interface))
        self._register_tool(TaskDelegator(ui_interface, conversation_agent))
        self._register_tool(CommandRunner())
        self._register_tool(TaskMemoryTool())
        self._register_tool(FileReader())
        self._register_tool(GrepSearch())
        self._register_tool(GitTools())
        self._register_tool(FileEditor())
        self._register_tool(WebSearch())

    def _register_tool(self, tool_instance: ToolInterface) -> None:
        try:
            name = tool_instance.get_tool_name()
            self.tools[name] = tool_instance
        except Exception:
            pass

    def get_tool(self, tool_name: str) -> ToolInterface:
        return self.tools.get(tool_name)

    def get_all_tools(self) -> Dict[str, ToolInterface]:
        return self.tools.copy()

    def _normalize_schema(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._normalize_schema(obj[k]) for k in sorted(obj.keys())}
        if isinstance(obj, list):
            return [self._normalize_schema(v) for v in obj]
        return obj

    def get_tools_description(self) -> List[Dict[str, Any]]:
        descriptions: List[Dict[str, Any]] = []
        for tool_name, tool_instance in sorted(self.tools.items(), key=lambda kv: kv[0]):
            try:
                raw_schema = tool_instance.json_schema()
                normalized = self._normalize_schema(raw_schema)
                descriptions.append(normalized)
            except Exception:
                continue
        return descriptions

    async def run_tool(self, tool_name: str, **kwargs):
        tool = self.tools.get(tool_name)
        try:
            if tool:
                return await tool.act(**kwargs)
        except Exception as e:
            return f"Error occurred while running tool '{tool_name}': {str(e)}"
        return "Tool not found"

    def get_tool_status(self, tool_name: str) -> str:
        tool = self.tools.get(tool_name)
        if tool:
            try:
                return tool.get_status()
            except Exception:
                return "Unknown status"
        return "Tool not found"
