import asyncio
import json
import sys
import os
from dotenv import load_dotenv
from pathlib import Path
current_dir = os.path.dirname(os.path.abspath(__file__))
python_dir = os.path.join(current_dir, 'python')
sys.path.insert(0, current_dir)
sys.path.insert(0, python_dir)

from python.core.agent import AgentLoop
from python.core.client import APIClient
from python.core.permissions import PermissionManager
from python.tools import TOOLS_DEFINITIONS, TOOL_MAPPING
from python.prompts.prompt import SYSTEM_PROMPT

load_dotenv()

class TerminalBridge:
    def __init__(self):
        self.approval_queue = asyncio.Queue()
        self.message_queue = asyncio.Queue()
        self.current_task = None
        self.stop_event = asyncio.Event()
        self.permission_manager = PermissionManager()
        model_name = os.getenv("OPENAI_MODEL")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        api_client = APIClient(api_key=openai_api_key, model_name=model_name)
        
        self.agent = AgentLoop(
            client=api_client,
            tools=TOOLS_DEFINITIONS,
            tool_mapping=TOOL_MAPPING,
            model_name=model_name,
            system_prompt=SYSTEM_PROMPT,
            stop_event=self.stop_event
        )
        
        # Pass stop_event to API client so it can check during streaming
        api_client.stop_event = self.stop_event

        self.agent.on_tool_request = self.request_tool_approval
        self.agent.on_content_chunk = self.send_content_chunk
        self.agent.on_response_complete = self.send_response_complete
        self._send_environment_info()
    
    def _send_environment_info(self):
        env_info = self.agent.tool_mapping["get_environment_info"]()
        working_dir = ""
        for line in env_info.split('\n'):
            if line.startswith("Working directory:"):
                working_dir = line.replace("Working directory: ", "")
                break
        from python.tools import fs
        fs.root = Path(working_dir).resolve()
        self.send_message("environment_info", {
            "working_directory": working_dir
        })
    
    def send_message(self, msg_type, data):
        message = json.dumps({"type": msg_type, "data": data})
        print(f"__MSG__{message}__END__", flush=True)
    
    def send_content_chunk(self, chunk):
        if not self.stop_event.is_set():
            self.send_message("agent_response_chunk", {"content": chunk})
    
    def send_response_complete(self, content):
        if not self.stop_event.is_set():
            self.send_message("agent_response_complete", {"content": content})
    
    async def request_tool_approval(self, tool_name, tool_args):
        if self.stop_event.is_set():
            return False, False
        
        stored_permission = self.permission_manager.check_permission(tool_name)
        
        if stored_permission is not None:
            if stored_permission:
                display_args = tool_args.get('path') or tool_args.get('query') or str(tool_args)
                self.send_message("tool_executing", {"name": tool_name, "args": display_args, "auto_approved": True})
            return stored_permission, False
        
        display_args = tool_args.get('path') or tool_args.get('query') or str(tool_args)
        self.send_message("tool_request", {"name": tool_name, "args": display_args, "all_args": tool_args})
        
        approved, remember = await asyncio.wait_for(self.approval_queue.get(), timeout=300)
        
        if self.stop_event.is_set():
            return False, False
        
        if remember:
            self.permission_manager.set_permission(tool_name, approved)
        
        if approved:
            self.send_message("tool_executing", {"name": tool_name, "args": display_args})
        else:
            self.send_message("tool_denied", {"name": tool_name, "args": display_args})
        
        return approved, remember
    
    async def process_user_input(self, user_input):
        self.stop_event.clear()
        self.send_message("thinking", {})
        result = await self.agent.run(user_input)
        if not self.stop_event.is_set():
            self.send_message("complete", {"result": result})
    
    async def force_interrupt_and_process(self, user_input):
        self.stop_event.set()
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            try:
                await asyncio.wait_for(self.current_task, timeout=0.5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        while not self.message_queue.empty():
            self.message_queue.get_nowait()
        while not self.approval_queue.empty():
            self.approval_queue.get_nowait()
        
        await asyncio.sleep(0.05)
        self.agent.messages = []
        self.send_message("interrupted", {})
        self.current_task = asyncio.create_task(self.process_user_input(user_input))
    
    async def stop_agent(self):
        self.stop_event.set()
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            try:
                await asyncio.wait_for(self.current_task, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        while not self.message_queue.empty():
            self.message_queue.get_nowait()
        while not self.approval_queue.empty():
            self.approval_queue.get_nowait()
        
        self.send_message("stopped", {})
    
    async def handle_stdin(self, loop):
        def stdin_ready():
            line = sys.stdin.readline()
            return line if line else None
        
        while True:
            line = await loop.run_in_executor(None, stdin_ready)
            if not line:
                break
            
            data = json.loads(line.strip())
            msg_type = data.get("type")
            payload = data.get("data", {})
            
            if msg_type == "user_input":
                self.current_task = asyncio.create_task(self.process_user_input(payload["message"]))
            elif msg_type == "tool_approval":
                await self.approval_queue.put((payload["approved"], payload.get("remember", False)))
            elif msg_type == "stop_agent":
                await self.stop_agent()
            elif msg_type == "force_interrupt":
                await self.force_interrupt_and_process(payload["message"])
                    
    def run(self):
        self.send_message("ready", {})
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.handle_stdin(loop))
        loop.close()

if __name__ == "__main__":
    bridge = TerminalBridge()
    bridge.run()