import json
import re
from typing import TYPE_CHECKING

from hakken.utils.json_utils import parse_tool_arguments
from hakken.prompts.reminders import get_reminders

if TYPE_CHECKING:
    from hakken.tools.manager import ToolManager
    from hakken.terminal_bridge import UIManager

class ToolExecutor:
    
    ERROR_PATTERNS = [
        (r'File "([^"]+)", line (\d+)', r'File "\1:\2"'),
        (r'^\s+at .+\n', ''),
        (r'\n\s*\n+', '\n'),
    ]
    
    def __init__(
        self, 
        tool_manager: "ToolManager", 
        ui_manager: "UIManager",
        add_message_callback,
        max_error_length: int = 800
    ):
        self._tool_manager = tool_manager
        self._ui_manager = ui_manager
        self._add_message = add_message_callback
        self._max_error_length = max_error_length

    def _compact_error(self, error: str) -> str:
        if len(error) <= self._max_error_length:
            return error
        
        for pattern, replacement in self.ERROR_PATTERNS:
            error = re.sub(pattern, replacement, error, flags=re.MULTILINE)
        
        if len(error) <= self._max_error_length:
            return error.strip()
        
        lines = error.strip().split('\n')
        if len(lines) <= 6:
            return error[:self._max_error_length]
        
        head = '\n'.join(lines[:2])
        tail = '\n'.join(lines[-3:])
        omitted = len(lines) - 5
        return f"{head}\n[...{omitted} lines omitted...]\n{tail}"

    async def handle_tool_calls(self, tool_calls) -> None:
        for i, tool_call in enumerate(tool_calls):
            is_last_tool = (i == len(tool_calls) - 1)
            
            args, error = parse_tool_arguments(tool_call.function.arguments)
            if error:
                self._add_tool_response(tool_call, json.dumps({"error": error}), is_last_tool)
                continue

            need_user_approve = args.get('need_user_approve', False)
            should_execute = True

            if need_user_approve:
                approval_content = f"Tool: {tool_call.function.name}, args: {args}"
                should_execute, content = await self._ui_manager.wait_for_user_approval(approval_content)

            if should_execute:
                await self._execute_tool(tool_call, args, is_last_tool)
            else:
                self._add_tool_response(
                    tool_call, 
                    f"user denied to execute tool, user input: {content}", 
                    is_last_tool
                )

    async def _execute_tool(self, tool_call, args: dict, is_last_tool: bool = False) -> None:
        tool_args = {k: v for k, v in args.items() if k != 'need_user_approve'}
        self._ui_manager.show_preparing_tool(tool_call.function.name, tool_args)
        
        tool_response = await self._safe_run_tool(tool_call.function.name, tool_args)
        success = "error" not in tool_response
        
        self._ui_manager.show_tool_execution(
            tool_call.function.name, 
            tool_args, 
            success=success, 
            result=str(tool_response)
        )
        self._add_tool_response(tool_call, json.dumps(tool_response), is_last_tool)

    async def _safe_run_tool(self, tool_name: str, tool_args: dict) -> dict:
        result = await self._tool_manager.run_tool(tool_name, **tool_args)
        if isinstance(result, str) and result.startswith("Error"):
            return {"error": self._compact_error(result)}
        if isinstance(result, dict) and "error" in result:
            result["error"] = self._compact_error(str(result["error"]))
            return result
        return result if isinstance(result, dict) else {"result": result}

    def _add_tool_response(self, tool_call, content: str, is_last_tool: bool = False) -> None:
        tool_content = [{"type": "text", "text": content}]
        
        if is_last_tool:
            reminder_content = get_reminders(self._tool_manager)
            tool_content.append({"type": "text", "text": reminder_content})
        
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": tool_content
        }
        self._add_message(tool_message)
