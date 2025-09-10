import json
import asyncio
import contextlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from interface.user_interface import HakkenCodeUI
from tools.tool_manager import ToolManager
from tools.human_interrupt import InterruptConfigManager
from agent.state_manager import StateManager


@dataclass
class ToolExecutionEntry:
    index: int
    tool_call: Any
    name: str
    args: Dict[str, Any]
    should_execute: bool = True


class ToolExecutionError(Exception):
    pass


class ToolExecutor:
    
    def __init__(self, ui_interface: HakkenCodeUI, tool_registry: ToolManager, 
                 interrupt_manager: InterruptConfigManager, state_manager: StateManager, prompt_manager=None):
        self.ui_interface = ui_interface
        self.tool_registry = tool_registry
        self.interrupt_manager = interrupt_manager
        self.state_manager = state_manager
        self.prompt_manager = prompt_manager
        self.logger = logging.getLogger(__name__)
    
    async def handle_tool_execution(self, response_message: Any, history_manager) -> None:
        if not hasattr(self.ui_interface, '_spinner_active') or not self.ui_interface._spinner_active:
            self.ui_interface.start_spinner("Processing…")
            self._start_interrupt_flow()
        
        tool_calls = self._extract_tool_calls(response_message)
        await self._process_tool_calls(tool_calls, history_manager)
    
    async def _process_tool_calls(self, tool_calls: List[Any], history_manager) -> None:
        pending_instruction = self._extract_pending_instruction()
        entries = self._parse_tool_calls(tool_calls)
        await self._apply_approvals(entries)

        parallel_entries, sequential_entries = self._partition_tool_entries(entries)
        self._handle_skipped_tools(tool_calls, entries, pending_instruction, history_manager)

        last_index = len(tool_calls) - 1 if tool_calls else -1
        await self._execute_parallel_tools(parallel_entries, sequential_entries, last_index, pending_instruction, history_manager)
        await self._execute_sequential_tools(sequential_entries, last_index, pending_instruction, history_manager)
    
    def _extract_pending_instruction(self) -> str:
        pending = self.state_manager.state.pending_user_instruction.strip()
        if pending:
            self.state_manager.state.pending_user_instruction = ""
        return pending
    
    def _parse_tool_calls(self, tool_calls: List[Any]) -> List[ToolExecutionEntry]:
        entries = []
        for idx, tool_call in enumerate(tool_calls):
            try:
                args = json.loads(tool_call.function.arguments)
                entries.append(ToolExecutionEntry(
                    index=idx,
                    tool_call=tool_call,
                    name=tool_call.function.name,
                    args=args,
                    should_execute=True
                ))
            except json.JSONDecodeError as e:
                self.ui_interface.display_error(f"Tool parameter parsing failed: {e}")
        return entries
    
    async def _apply_approvals(self, entries: List[ToolExecutionEntry]) -> None:
        for entry in entries:
            try:
                if self.interrupt_manager.requires_approval(entry.name, entry.args):
                    entry.should_execute = await self._get_tool_approval(entry)
            except Exception as e:
                self.logger.error(f"Approval process failed for {entry.name}: {e}")
                entry.should_execute = False
    
    async def _get_tool_approval(self, entry: ToolExecutionEntry) -> bool:
        approval_content = self._format_approval_preview(entry.name, entry.args)
        approval_result = await self.ui_interface.confirm_action(approval_content)
        
        if isinstance(approval_result, str):
            decision = approval_result.strip().lower()
            if decision == "always":
                with contextlib.suppress(Exception):
                    self.interrupt_manager.set_always_allow(entry.name, entry.args)
            return decision in ("yes", "always")
        
        return bool(approval_result)
    
    def _partition_tool_entries(self, entries: List[ToolExecutionEntry]) -> Tuple[List[ToolExecutionEntry], List[ToolExecutionEntry]]:
        parallel_entries = [
            e for e in entries 
            if e.should_execute and self._is_parallel_safe(e.name, e.args)
        ]
        sequential_entries = [
            e for e in entries 
            if e.should_execute and not self._is_parallel_safe(e.name, e.args)
        ]
        return parallel_entries, sequential_entries
    
    def _handle_skipped_tools(self, tool_calls: List[Any], entries: List[ToolExecutionEntry], 
                            pending_instruction: str, history_manager) -> None:
        skipped_indices = {e.index for e in entries if not e.should_execute}
        for idx in skipped_indices:
            tool_call = tool_calls[idx]
            self._add_tool_response(
                tool_call, 
                f"Tool execution skipped: {pending_instruction}", 
                is_last_tool=(idx == len(tool_calls) - 1),
                history_manager=history_manager
            )
    
    async def _execute_parallel_tools(
        self, 
        parallel_entries: List[ToolExecutionEntry], 
        sequential_entries: List[ToolExecutionEntry], 
        last_index: int, 
        pending_instruction: str,
        history_manager
    ) -> None:
        if not parallel_entries:
            return

        if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
            self.ui_interface.update_spinner_text(f"Running {len(parallel_entries)} tools in parallel…")

        tasks = [self._execute_single_tool_async(entry, pending_instruction) for entry in parallel_entries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            entry = parallel_entries[i]
            if isinstance(result, Exception):
                content = f"Tool call failed, fail reason: {str(result)}"
                self.logger.error(f"Parallel tool {entry.name} failed: {result}")
            else:
                content = json.dumps(result)
            
            self._add_tool_response(
                entry.tool_call, 
                content, 
                is_last_tool=(entry.index == last_index and not sequential_entries),
                history_manager=history_manager
            )
    
    async def _execute_sequential_tools(
        self, 
        sequential_entries: List[ToolExecutionEntry], 
        last_index: int, 
        pending_instruction: str,
        history_manager
    ) -> None:
        for entry in sequential_entries:
            await self._execute_single_tool(
                entry.tool_call,
                entry.args,
                is_last_tool=(entry.index == last_index),
                user_response=pending_instruction,
                history_manager=history_manager
            )
    
    async def _execute_single_tool_async(self, entry: ToolExecutionEntry, user_response: str) -> Any:
        tool_args = self._prepare_tool_args(entry.args, user_response)
        return await self.tool_registry.run_tool(entry.name, **tool_args)
    
    async def _execute_single_tool(
        self, 
        tool_call: Any, 
        args: Dict[str, Any], 
        is_last_tool: bool = False, 
        user_response: str = "",
        history_manager = None
    ) -> None:
        tool_args = self._prepare_tool_args(args, user_response)
        
        self._update_tool_status(tool_call.function.name, "running")
        
        try:
            tool_response = await self.tool_registry.run_tool(tool_call.function.name, **tool_args)
            self._update_tool_status(tool_call.function.name, "completed")
            await asyncio.sleep(self.state_manager.agent_config.STATUS_DISPLAY_DELAY)
            
            response_content = json.dumps(tool_response)
            if user_response:
                response_content += f" (User instructions: {user_response})"
                
            self._add_tool_response(tool_call, response_content, is_last_tool, history_manager)
            
        except Exception as e:
            self.logger.error(f"Tool {tool_call.function.name} failed: {e}")
            self._update_tool_status(tool_call.function.name, "failed")
            await asyncio.sleep(self.state_manager.agent_config.STATUS_DISPLAY_DELAY)
            
            self._add_tool_response(
                tool_call, 
                f"Tool call failed, fail reason: {str(e)}", 
                is_last_tool,
                history_manager
            )
    
    def _prepare_tool_args(self, args: Dict[str, Any], user_response: str) -> Dict[str, Any]:
        tool_args = {k: v for k, v in args.items() if k != 'need_user_approve'}
        if user_response:
            tool_args['user_instructions'] = user_response
        return tool_args
    
    def _update_tool_status(self, tool_name: str, status: str) -> None:
        status_messages = {
            "running": f"Running {tool_name}...",
            "completed": f"✓ {tool_name} completed",
            "failed": f"✗ {tool_name} failed"
        }
        
        if hasattr(self.ui_interface, '_spinner_active') and self.ui_interface._spinner_active:
            self.ui_interface.update_spinner_text(status_messages[status])
        else:
            if status == "completed":
                self.ui_interface.display_success(f"{tool_name} completed successfully")
            elif status == "failed":
                self.ui_interface.display_error(f"{tool_name} failed")
            else:
                self.ui_interface.display_info(f"🔧 {tool_name}...")
    
    def _is_parallel_safe(self, tool_name: str, args: Dict[str, Any]) -> bool:
        parallel_safe_tools = {"read_file", "grep_search", "git_tools", "task_memory", "web_search"}
        if tool_name not in parallel_safe_tools:
            return False
        if tool_name == "task_memory":
            action = str(args.get("action", "")).strip().lower()
            return action in ("recall", "similar")
        return True
    
    def _format_approval_preview(self, tool_name: str, args: Dict[str, Any]) -> str:
        try:
            preview_args = self._create_preview_args(tool_name, args)
            return f"Tool: {tool_name}, args: {preview_args}"
        except Exception:
            return f"Tool: {tool_name}, args: {args}"
    
    def _create_preview_args(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        preview_args: Dict[str, Any] = {}
        
        if tool_name == "cmd_runner":
            return self._format_command_preview(args)
        
        for k, v in args.items():
            if isinstance(v, str):
                preview_args[k] = self.state_manager.truncate_string(v, self.state_manager.agent_config.ARGS_PREVIEW_MAX_LENGTH)
            else:
                preview_args[k] = v
        
        return preview_args
    
    def _format_command_preview(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cmd = args.get("command", "")
        if isinstance(cmd, str):
            normalized = cmd.replace("\n", " ")
            truncated = self.state_manager.truncate_string(normalized, self.state_manager.agent_config.COMMAND_PREVIEW_MAX_LENGTH)
            return {
                "command": truncated,
                "length": len(cmd)
            }
        else:
            return {"command": str(cmd)}
    
    def _extract_tool_calls(self, response_message: Any) -> List[Any]:
        return response_message.tool_calls if hasattr(response_message, 'tool_calls') and response_message.tool_calls else []
    
    def _add_tool_response(self, tool_call: Any, content: str, is_last_tool: bool = False, history_manager = None) -> None:
        if history_manager is None:
            return
            
        tool_content = [{"type": "text", "text": content}]
        
        if is_last_tool:
            # Add reminder content for the last tool to help continue the conversation
            if self.prompt_manager:
                try:
                    reminder_content = self.prompt_manager.get_reminder()
                    if reminder_content:
                        tool_content.append({"type": "text", "text": reminder_content})
                except:
                    # Fallback reminder if prompt manager call fails
                    tool_content.append({"type": "text", "text": "Continue with your response."})
            else:
                # Fallback reminder if prompt manager is not available
                tool_content.append({"type": "text", "text": "Continue with your response and complete the task."})
        
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": tool_content
        }
        history_manager.add_message(tool_message)
    
    def _start_interrupt_flow(self) -> None:
        with contextlib.suppress(Exception):
            self.ui_interface.display_interrupt_hint()
        with contextlib.suppress(Exception):
            self.ui_interface.start_interrupt_listener()
