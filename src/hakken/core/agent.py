from hakken.core.client import APIClient
from hakken.core.message_builder import MessageBuilder
from hakken.core.response_handler import ResponseHandler
from hakken.core.tool_executor import ToolExecutor
from hakken.prompts.manager import PromptManager
from hakken.tools.manager import ToolManager
from hakken.history.manager import HistoryManager
from hakken.subagents.manager import SubagentManager
from hakken.terminal_bridge import UIManager

################ Main Agent ################

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
        
        self._response_handler = ResponseHandler(ui_manager)
        self._tool_executor = ToolExecutor(
            tool_manager, 
            ui_manager, 
            self.add_message
        )

    @property
    def messages(self):
        return self._history_manager.get_current_messages()
    
    def add_message(self, message):
        self._history_manager.add_message(message)

    async def start_conversation(self):
        self.add_message(
            MessageBuilder.create_system_message(
                self._prompt_manager.get_system_prompt()
            )
        )
        
        user_input = await self._ui_manager.get_user_input()
        self.add_message(MessageBuilder.create_user_message(user_input))

        await self._recursive_message_handling()

    async def start_task(self, task_system_prompt: str, user_input: str) -> str:
        self._is_in_task = True
        self._history_manager.start_new_chat()
        
        self.add_message(MessageBuilder.create_system_message(task_system_prompt))
        self.add_message(MessageBuilder.create_user_message(user_input))

        await self._recursive_message_handling()
        self._is_in_task = False
        return self._history_manager.finish_chat_get_response()

    async def _recursive_message_handling(self):
        self._history_manager.auto_messages_compression()

        request = self._build_api_request()
        
        self._ui_manager.print_simple_message("", "🤖")
        
        stream_generator = self._api_client.get_completion_stream(request)
        
        if stream_generator is None:
            raise Exception("Stream generator is None - API client returned no response")
        
        response_message, _, token_usage = self._response_handler.process_stream(
            stream_generator
        )
            
        if token_usage:
            self._history_manager.update_token_usage(token_usage)
        
        assistant_message = self._build_assistant_message(response_message)
        self.add_message(assistant_message)
        
        self._history_manager.auto_messages_compression()

        if ResponseHandler.has_tool_calls(response_message) and len(response_message.tool_calls) > 0:
            await self._tool_executor.handle_tool_calls(response_message.tool_calls)
            self._print_context_window_and_total_cost()
            await self._recursive_message_handling()
        else:
            self._print_context_window_and_total_cost()
            await self._handle_conversation_turn(response_message)

    def _build_api_request(self) -> dict:
        messages = MessageBuilder.apply_cache_control(
            self._history_manager.get_current_messages()
        )
        return {
            "messages": messages,
            "tools": self._tool_manager.get_tools_description(),
        }

    def _build_assistant_message(self, response_message) -> dict:
        has_tool_calls = ResponseHandler.has_tool_calls(response_message)
        content = response_message.content or ""
        trimmed_content = ResponseHandler.get_trimmed_content(content)
        
        assistant_message = MessageBuilder.create_assistant_message(
            content=response_message.content if response_message.content else None,
            tool_calls=response_message.tool_calls if has_tool_calls else None
        )
        
        if not has_tool_calls and not trimmed_content:
            self._ui_manager.print_info(
                "[agent-debug] assistant returned empty response, using fallback message"
            )
            assistant_message["content"] = MessageBuilder.create_fallback_content()
        
        return assistant_message

    async def _handle_conversation_turn(self, response_message):
        has_tool_calls = ResponseHandler.has_tool_calls(response_message)
        content = response_message.content or ""
        trimmed_content = ResponseHandler.get_trimmed_content(content)
        
        if self._is_in_task or self._is_bridge_mode:
            if not has_tool_calls:
                self._ui_manager.print_info(
                    f"[agent-debug] turn completed without tool call | len={len(trimmed_content)}"
                )
            return
        
        user_input = await self._ui_manager.get_user_input()
        self.add_message(MessageBuilder.create_user_message(user_input))
        await self._recursive_message_handling()

    def _print_context_window_and_total_cost(self):
        self._ui_manager.print_simple_message(
            f"(context window: {self._history_manager.current_context_window}%, "
            f"total cost: {self._api_client.total_cost}$)"
        )

    def print_streaming_content(self, content):
        self._ui_manager.print_streaming_content(content)