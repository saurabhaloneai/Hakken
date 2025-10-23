import json
import asyncio

class AgentLoop:
    def __init__(self, client, tools, tool_mapping, model_name, system_prompt=None, stop_event=None):
        self.client = client
        self.tools = tools
        self.tool_mapping = tool_mapping
        self.model_name = model_name
        self.messages = []
        self.max_iterations = 50
        self.system_prompt = system_prompt
        self.on_tool_request = None
        self.on_content_chunk = None
        self.on_response_complete = None
        self.stop_event = stop_event
        self._initialize_environment_info()

    def _initialize_environment_info(self):
        env_info = self.tool_mapping["get_environment_info"]()
        listing = []
        if "list_directory" in self.tool_mapping:
            ls = self.tool_mapping["list_directory"](".")
            files = ls.get("files", [])
            listing = [f.get("path", f.get("name", "")) for f in files][:20]
        files_line = "\nProject files: " + (", ".join(listing) if listing else "(none)")
        env_context = f"## Environment Information\n{env_info}{files_line}\n\n"
        self.add_system_message(env_context)

    def add_system_message(self, content: str):
        self.messages.append({"role": "system", "content": content})

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

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
