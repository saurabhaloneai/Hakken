import json
from hakken.core.client import APIClient
from hakken.prompts.manager import PromptManager
from hakken.prompts.reminders import get_reminders
from hakken.tools.manager import ToolManager
from hakken.history.manager import HistoryManager
from hakken.subagents.manager import SubagentManager
from hakken.terminal_bridge import UIManager


class Agent:
   
    def __init__(
        self,
        tool_manager: ToolManager,
        api_client: APIClient,
        ui_manager: "UIManager",
        history_manager: HistoryManager,
        prompt_manager: PromptManager,
        subagent_manager: SubagentManager,
        is_bridge_mode: bool = False
    ):
        self._tool_manager = tool_manager
        self._api_client = api_client
        self._ui_manager = ui_manager
        self._history_manager = history_manager
        self._prompt_manager = prompt_manager
        self._subagent_manager = subagent_manager
        self._is_in_task = False
        self._is_bridge_mode = is_bridge_mode

    @property
    def messages(self):
        return self._history_manager.get_current_messages()
    
    def add_message(self, message):
        self._history_manager.add_message(message)

    async def start_conversation(self):
        system_message = {
            "role": "system", 
            "content": [
                {"type": "text", "text": self._prompt_manager.get_system_prompt()}
            ]
        }
        self.add_message(system_message)
        
        user_input = await self._ui_manager.get_user_input()
        user_message = {
            "role": "user", 
            "content": [
                {"type": "text", "text": user_input}
            ]
        }
        self.add_message(user_message)

        await self._recursive_message_handling()

    async def start_task(self, task_system_prompt: str, user_input: str) -> str:
        self._is_in_task = True
        self._history_manager.start_new_chat()
        system_message = {
            "role": "system", 
            "content": [
                {"type": "text", "text": task_system_prompt}
            ]
        }
        self.add_message(system_message)
        
        user_message = {
            "role": "user", 
            "content": [
                {"type": "text", "text": user_input}
            ]
        }
        self.add_message(user_message)

        await self._recursive_message_handling()
        self._is_in_task = False
        return self._history_manager.finish_chat_get_response()

    async def _recursive_message_handling(self):
        self._history_manager.auto_messages_compression()

        request = {
            "messages": self._get_messages_with_cache_mark(),
            "tools": self._tool_manager.get_tools_description(),
        }
        
        self._ui_manager.print_simple_message("", "🤖")
        
        stream_generator = self._api_client.get_completion_stream(request)
        
        if stream_generator is None:
            raise Exception("Stream generator is None - API client returned no response")
        
        response_message = None
        full_content = ""
        token_usage = None
        
        iterator = iter(stream_generator)
        
        self._ui_manager.start_stream_display()
        
        for chunk in iterator:
            if isinstance(chunk, str):
                full_content += chunk
                self._ui_manager.print_streaming_content(chunk)
            elif hasattr(chunk, 'role') and chunk.role == 'assistant':
                response_message = chunk
                if hasattr(chunk, 'usage') and chunk.usage:
                    token_usage = chunk.usage
                break
            elif hasattr(chunk, 'usage') and chunk.usage:
                token_usage = chunk.usage

        self._ui_manager.stop_stream_display()
        
        if response_message is None:
            response_message = self._create_simple_message(full_content)
            
        if token_usage:
            self._history_manager.update_token_usage(token_usage)
        
        has_tool_calls = hasattr(response_message, 'tool_calls') and response_message.tool_calls
        content = response_message.content or ""
        trimmed_content = self._get_trimmed_content(content)
        assistant_message = {
            "role": "assistant",
            "tool_calls": response_message.tool_calls if has_tool_calls else None
        }
        
        if response_message.content:
            assistant_message["content"] = response_message.content

        empty_response_without_tools = not has_tool_calls and not trimmed_content

        if empty_response_without_tools:
            self._ui_manager.print_info(
                "[agent-debug] assistant returned empty response, using fallback message"
            )
            fallback_text = "I didn't receive any content from the model. Please provide more detail or try again."
            assistant_message["content"] = [
                {"type": "text", "text": fallback_text}
            ]
            content = fallback_text
            trimmed_content = fallback_text.strip()
        
        self.add_message(assistant_message)
        
        self._history_manager.auto_messages_compression()

        if hasattr(response_message, 'tool_calls') and response_message.tool_calls is not None and len(response_message.tool_calls) > 0:
            await self._handle_tool_calls(response_message.tool_calls)
            self._print_context_window_and_total_cost()
            await self._recursive_message_handling()
        else:
            self._print_context_window_and_total_cost()
            if self._is_in_task or self._is_bridge_mode:
                trimmed = trimmed_content
                if not has_tool_calls:
                    self._ui_manager.print_info(
                        f"[agent-debug] turn completed without tool call | len={len(trimmed)}"
                    )
                return
            user_input = await self._ui_manager.get_user_input()
            user_message = {
                "role": "user", 
                "content": [
                    {"type": "text", "text": user_input}
                ]
            }
            self.add_message(user_message)
            await self._recursive_message_handling()

    def _print_context_window_and_total_cost(self):
        self._ui_manager.print_simple_message(
            f"(context window: {self._history_manager.current_context_window}%, "
            f"total cost: {self._api_client.total_cost}$)"
        )

    def _get_messages_with_cache_mark(self):
        messages = self._history_manager.get_current_messages()
        if messages and "content" in messages[-1] and messages[-1]["content"]:
            content = messages[-1]["content"]
            if isinstance(content, list) and len(content) > 0 and isinstance(content[-1], dict):
                content[-1]["cache_control"] = {"type": "ephemeral"}
            elif isinstance(content, str):
                messages[-1]["content"] = [
                    {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}
                ]
        return messages

    async def _handle_tool_calls(self, tool_calls):
        for i, tool_call in enumerate(tool_calls):
            is_last_tool = (i == len(tool_calls) - 1)
            
            args, error = self._parse_tool_args(tool_call.function.arguments)
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

    async def _execute_tool(self, tool_call, args, is_last_tool=False):
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
            return {"error": result}
        return result if isinstance(result, dict) else {"result": result}

    def _parse_tool_args(self, raw_args: str) -> tuple[dict, str | None]:
        if not raw_args:
            return {}, None
        decoded = json.JSONDecoder().decode(raw_args) if self._is_valid_json(raw_args) else None
        if decoded is None:
            return {}, f"Invalid JSON: {raw_args[:100]}"
        return (decoded, None) if isinstance(decoded, dict) else ({}, "Expected JSON object")

    def _is_valid_json(self, s: str) -> bool:
        idx = 0
        while idx < len(s):
            if s[idx] in ' \t\n\r':
                idx += 1
                continue
            return s[idx] in '{["' or s[idx:idx+4] in ('true', 'null') or s[idx:idx+5] == 'false' or s[idx].isdigit() or s[idx] == '-'
        return False

    def _add_tool_response(self, tool_call, content, is_last_tool=False):
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
        self.add_message(tool_message)

    def _create_simple_message(self, content):
        class SimpleMessage:
            def __init__(self, content):
                self.content = content
                self.role = "assistant"
                self.tool_calls = None
        
        return SimpleMessage(content)

    def _create_error_message(self, error_msg):
        class ErrorMessage:
            def __init__(self, error_msg):
                self.content = f"Sorry, I encountered a technical problem: {error_msg}"
                self.role = "assistant"
                self.tool_calls = None
        
        return ErrorMessage(error_msg)

    def print_streaming_content(self, content):
        self._ui_manager.print_streaming_content(content)

    def _get_trimmed_content(self, content) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_value = block.get("text", "")
                    if isinstance(text_value, str):
                        text_parts.append(text_value)
            return " ".join(text_parts).strip()
        return ""