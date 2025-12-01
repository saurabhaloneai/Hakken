import sys
import json
import asyncio
import os
import traceback
from typing import Optional, Any, Callable, Tuple, List, Dict


class UIManager:
    def __init__(self, send_callback: Optional[Callable[[str, Any], None]] = None):
        self._send_callback = send_callback
        self._is_bridge_mode = send_callback is not None
        self._approval_future: Optional[asyncio.Future] = None
        self._streaming = False
    
    def _send(self, msg_type: str, data: Any = None):
        if self._send_callback:
            self._send_callback(msg_type, data or {})
    
    async def get_user_input(self) -> str:
        if self._is_bridge_mode:
            raise RuntimeError("get_user_input should not be called in bridge mode")
        try:
            return input("\n> ").strip()
        except EOFError:
            return "exit"
    
    def print_simple_message(self, message: str, prefix: str = ""):
        if self._is_bridge_mode:
            self._send("message", {"content": message, "prefix": prefix})
        else:
            print(f"{prefix} {message}" if prefix else message)
    
    def print_assistant_message(self, message: str):
        if self._is_bridge_mode:
            self._send("assistant_message", {"content": message})
        else:
            print(f"🤖 {message}")
    
    def print_info(self, message: str):
        if self._is_bridge_mode:
            self._send("info", {"content": message})
        else:
            print(f"ℹ️  {message}")
    
    def start_stream_display(self):
        self._streaming = True
        if self._is_bridge_mode:
            self._send("stream_start", {})
    
    def print_streaming_content(self, chunk: str):
        if self._is_bridge_mode:
            self._send("stream_chunk", {"content": chunk})
        else:
            print(chunk, end="", flush=True)
    
    def stop_stream_display(self):
        self._streaming = False
        if self._is_bridge_mode:
            self._send("stream_end", {})
        else:
            print()
    
    def show_preparing_tool(self, tool_name: str, args: Dict[str, Any]):
        if self._is_bridge_mode:
            self._send("tool_preparing", {"name": tool_name, "args": args})
        else:
            print(f"🔧 Preparing: {tool_name}")
    
    def show_tool_execution(self, tool_name: str, args: Dict[str, Any], success: bool, result: str):
        if self._is_bridge_mode:
            self._send("tool_result", {"name": tool_name, "args": args, "success": success, "result": result})
        else:
            status = "✅" if success else "❌"
            print(f"{status} {tool_name}: {result[:200]}...")
    
    async def wait_for_user_approval(self, content: str) -> Tuple[bool, str]:
        if self._is_bridge_mode:
            self._send("approval_request", {"content": content})
            loop = asyncio.get_event_loop()
            self._approval_future = loop.create_future()
            result = await self._approval_future
            self._approval_future = None
            return result
        else:
            print(f"\n⚠️  Approval required:\n{content}")
            response = input("Approve? (y/n): ").strip().lower()
            return (response == 'y', response)
    
    def resolve_approval(self, approved: bool, content: str = ""):
        if self._approval_future and not self._approval_future.done():
            self._approval_future.set_result((approved, content))
    
    def display_todos(self, todos: List[Dict[str, Any]]):
        if self._is_bridge_mode:
            self._send("todos", {"items": todos})
        else:
            print("\n📋 Todo List:")
            for todo in todos:
                status_icon = {"pending": "⬜", "in_progress": "🔄", "completed": "✅"}.get(todo.get("status", "pending"), "⬜")
                print(f"  {status_icon} [{todo.get('id', '?')}] {todo.get('content', '')}")
            print()


from hakken.core.factory import AgentFactory


class Bridge:
    def __init__(self):
        self.agent = None
        self.ui: Optional[UIManager] = None
        self.task: Optional[asyncio.Task] = None
        self.stop_requested = False
        self.turn_status: Dict[str, Any] = {"state": "idle", "reason": ""}
        
    def emit(self, msg_type: str, data: Any = None):
        output = f"__MSG__{json.dumps({'type': msg_type, 'data': data or {}})}__END__"
        print(output, flush=True)

    def set_turn_status(self, state: str, reason: str = ""):
        self.turn_status = {"state": state, "reason": reason}
        self.emit("turn_status", self.turn_status)

    def _record_stop_notice(self):
        if not self.agent:
            return
        messages = self.agent.messages
        if not messages or len(messages) <= 1:
            return

        notice = {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Execution was interrupted by the user before it completed. "
                        "When you respond next, briefly acknowledge the interruption and wait for the user's "
                        "instructions before resuming any outstanding work."
                    )
                }
            ]
        }
        self.agent.add_message(notice)
    
    def create_agent(self):
        self.ui = UIManager(self.emit)
        self.agent = AgentFactory.create_agent(ui_manager=self.ui, is_bridge_mode=True)
        
    async def handle_input(self, message: str):
        self.stop_requested = False
        self.set_turn_status("running", "processing user request")
        self.agent.add_message({
            "role": "user",
            "content": [{"type": "text", "text": message}]
        })
        await self.agent._recursive_message_handling()
        if not self.stop_requested:
            self.set_turn_status("done", "turn completed")
            self.emit("complete")
    
    async def handle_approval(self, approved: bool, content: str = ""):
        if self.ui:
            self.ui.resolve_approval(approved, content)
    
    async def handle_stop(self):
        self.stop_requested = True
        had_active_task = self.task and not self.task.done()
        if had_active_task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            finally:
                self.task = None
            self._record_stop_notice()
        if self.ui:
            self.ui.resolve_approval(False, "agent stopped")
        self.set_turn_status("blocked", "stopped by user")
        self.emit("stopped")
    
    async def handle_interrupt(self, message: str):
        self.stop_requested = True
        self.set_turn_status("interrupted", "user forced new input")
        if self.task and not self.task.done():
            self.task.cancel()
        self.task = asyncio.create_task(self.handle_input(message))
        await self.task
    
    async def process(self, msg: dict):
        msg_type = msg.get("type")
        data = msg.get("data", {})
        
        if msg_type == "user_input":
            self.task = asyncio.create_task(self.handle_input(data.get("message", "")))
            await self.task
        elif msg_type == "tool_approval":
            await self.handle_approval(data.get("approved", False), data.get("content", ""))
        elif msg_type == "stop_agent":
            await self.handle_stop()
        elif msg_type == "force_interrupt":
            await self.handle_interrupt(data.get("message", ""))
    
    async def read_stdin(self):
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            await self.process(json.loads(line))
    
    async def run(self):
        self.emit("environment_info", {"working_directory": os.getcwd()})
        self.create_agent()
        self.agent.add_message({
            "role": "system",
            "content": [{"type": "text", "text": self.agent._prompt_manager.get_system_prompt()}]
        })
        self.set_turn_status("idle", "waiting for input")
        self.emit("ready")
        await self.read_stdin()


def main():
    asyncio.run(Bridge().run())


if __name__ == "__main__":
    main()
