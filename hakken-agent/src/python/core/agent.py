import json
import asyncio
from typing import Optional
from .message import system_message, user_message
from .conversation import ConversationHistory

class AgentLoop:
    def __init__(self, client, tools, tool_mapping, model_name, system_prompt=None, stop_event=None, use_structured_history=False):
        self.client = client
        self.tools = tools
        self.tool_mapping = tool_mapping
        self.model_name = model_name
        self.use_structured_history = use_structured_history
        self.conversation = ConversationHistory()
        self.messages = [] 
        self.max_iterations = 50
        self.system_prompt = system_prompt
        self.on_tool_request = None
        self.on_content_chunk = None
        self.on_response_complete = None
        self.stop_event = stop_event
        self._initialize_environment_info()

    def add_system_message(self, content: str, metadata: Optional[dict] = None):
        if self.use_structured_history:
            self.conversation.add_system(content, metadata)
            self.messages = self.conversation.get_messages_for_api()
        else:
            msg = system_message(content)
            self.messages.append(msg.model_dump(exclude={'metadata', 'timestamp'}))

    def add_user_message(self, content: str, metadata: Optional[dict] = None):
        if self.use_structured_history:
            self.conversation.add_user(content, metadata)
            self.messages = self.conversation.get_messages_for_api()
        else:
            msg = user_message(content)
            self.messages.append(msg.model_dump(exclude={'metadata', 'timestamp'}))

    def _execute_tool_call(self, tool_call):
        tool_name = tool_call['function']['name']
        tool_args = json.loads(tool_call['function']['arguments'])
        return self.tool_mapping[tool_name](**tool_args)

    async def _handle_tool_calls(self, content, tool_calls):
        self.messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

        for tool_call in tool_calls:
            tool_name = tool_call['function']['name']
            tool_args = json.loads(tool_call['function']['arguments'])

            if self.on_tool_request:
                approved, remember = await self.on_tool_request(tool_name, tool_args)
            else:
                approved = True
                remember = False

            result = self._execute_tool_call(tool_call) if approved else {"error": "User denied tool execution"}
            self.messages.append({"role": "tool", "tool_call_id": tool_call['id'], "content": json.dumps(result, indent=2)})

        return True

    async def run(self, user_input: str) -> str:
        self.add_user_message(user_input)
        iteration = 0

        while iteration < self.max_iterations:
            if self.stop_event and self.stop_event.is_set():
                raise asyncio.CancelledError("Stop requested")

            iteration += 1
            content, tool_calls = await self.client.stream_chat(self.messages, self.tools, on_content_chunk=self.on_content_chunk)

            if self.stop_event and self.stop_event.is_set():
                raise asyncio.CancelledError("Stop requested")

            if self.on_response_complete and content and not tool_calls:
                self.on_response_complete(content)

            if tool_calls:
                await self._handle_tool_calls(content, tool_calls)
            else:
                self.messages.append({"role": "assistant", "content": content})
                return content

        return "Max iteration limit reached"
