import re
import os 
import json
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, get_type_hints
from datetime import datetime
import inspect
import anthropic

class LanguageModelLike:
    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        raise NotImplementedError

class Tool:
    def __init__(self, name: str, func: Callable, description: str = ""):
        self.name = name
        self.func = func
        self.description = description

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        hints = get_type_hints(self.func)
        validated = {}
        
        for param, value in params.items():
            expected_type = hints.get(param)
            if expected_type and not isinstance(value, expected_type):
                validated[param] = expected_type(value)
            else:
                validated[param] = value
        return validated

    def get_schema(self) -> Dict[str, Any]:
        hints = get_type_hints(self.func)
        sig = inspect.signature(self.func)
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'return':
                continue
            
            param_type = hints.get(param_name, str)
            type_map = {int: "integer", float: "number", bool: "boolean", str: "string"}
            prop_type = type_map.get(param_type, "string")
            
            properties[param_name] = {"type": prop_type}
            
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {"type": "object", "properties": properties, "required": required}
        }

class AnthropicModel(LanguageModelLike):
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, max_retries: int = 3) -> Dict[str, Any]:
        system_msg, conv_msgs = self._split_messages(messages)
        kwargs = {
            "model": self.model, 
            "max_tokens": 4096,
            "messages": conv_msgs,
            "stream": False
        }
        
        if system_msg:
            kwargs["system"] = system_msg
        if tools:
            kwargs["tools"] = tools
        
        for attempt in range(max_retries):
            try:
                resp = self.client.messages.create(**kwargs)
                return self._parse_response(resp)
            except anthropic.RateLimitError as e:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                return {"text": f"Rate limit exceeded after {max_retries} attempts", "tool_calls": [], "stop_reason": "error"}
            except anthropic.APIStatusError as e:
                if e.status_code == 529 and attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                return {"text": f"API error: {e}", "tool_calls": [], "stop_reason": "error"}
            except Exception as e:
                return {"text": f"Model error: {e}", "tool_calls": [], "stop_reason": "error"}
        
        return {"text": "Max retries exceeded", "tool_calls": [], "stop_reason": "error"}
    
    def _split_messages(self, messages):
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        return system_msg, [m for m in messages if m["role"] != "system"]
    
    def _parse_response(self, resp):
        text = "".join(block.text for block in resp.content if block.type == "text")
        tool_calls = [{"id": block.id, "name": block.name, "input": block.input} 
                     for block in resp.content if block.type == "tool_use"]
        return {"text": text, "tool_calls": tool_calls, "stop_reason": resp.stop_reason}

class ConversationMemory:
    def __init__(self, max_messages: int = 100):
        self.messages: List[Dict[str, Any]] = []
        self.max_messages = max_messages
    
    def add_message(self, role: str, content: Any):
        self.messages.append({"role": role, "content": content, "timestamp": datetime.now()})
        if len(self.messages) > self.max_messages:
            system_messages = [m for m in self.messages if m["role"] == "system"]
            other_messages = [m for m in self.messages if m["role"] != "system"]
            keep_count = self.max_messages - len(system_messages)
            self.messages = system_messages + other_messages[-keep_count:]
    
    def get_messages(self) -> List[Dict[str, Any]]:
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]
    
    def clear(self):
        self.messages.clear()

def format_tool_result(result: Any) -> str:
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    elif isinstance(result, (list, tuple)):
        return "\n".join(f"- {item}" for item in result)
    elif isinstance(result, (int, float)) and abs(result) > 1000:
        return f"{result:,}"
    return str(result)

def prepare_tools(tools: Optional[Sequence[Union[Tool, Callable]]]) -> tuple:
    tools_by_name: Dict[str, Tool] = {}
    tool_schemas: List[Dict[str, Any]] = []
    
    if tools:
        for t in tools:
            if isinstance(t, Tool):
                tool = t
            elif callable(t):
                name = getattr(t, "__name__", "unnamed_tool")
                desc = getattr(t, "__doc__", "No description provided.")
                tool = Tool(name, t, desc)
            
            tools_by_name[tool.name] = tool
            tool_schemas.append(tool.get_schema())
    
    return tools_by_name, tool_schemas

def run_agent_iteration(
    model: LanguageModelLike,
    messages: List[Dict[str, Any]],
    tools_by_name: Dict[str, Tool],
    tool_schemas: List[Dict[str, Any]],
    system_prompt: str
) -> tuple:
    model_resp = model.generate(
        [{"role": "system", "content": system_prompt}] + messages,
        tools=tool_schemas if tool_schemas else None
    )
    
    text = model_resp.get("text", "")
    tool_calls = model_resp.get("tool_calls", [])
    
    assistant_content = []
    if text:
        assistant_content.append({"type": "text", "text": text})
    
    for tool_call in tool_calls:
        assistant_content.append({
            "type": "tool_use",
            "id": tool_call["id"],
            "name": tool_call["name"],
            "input": tool_call["input"]
        })
    
    messages.append({"role": "assistant", "content": assistant_content})
    
    if tool_calls:
        tool_results = []
        for tool_call in tool_calls:
            name, tool_input, tool_id = tool_call["name"], tool_call["input"], tool_call["id"]
            
            tool = tools_by_name.get(name)
            if not tool:
                result, is_error = f"Unknown tool: {name}", True
            else:
                validated_input = tool.validate_params(tool_input)
                raw_result = tool(**validated_input)
                result, is_error = format_tool_result(raw_result), False
            
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result,
                "is_error": is_error
            })
        
        messages.append({"role": "user", "content": tool_results})
        return messages, text, True
    
    return messages, text, False

class Agent:
    def __init__(
        self,
        model: LanguageModelLike,
        prompt: str,
        tools_by_name: Dict[str, Tool],
        tool_schemas: List[Dict[str, Any]],
        max_iterations: int,
        memory: Optional[ConversationMemory]
    ):
        self.model = model
        self.prompt = prompt
        self.tools_by_name = tools_by_name
        self.tool_schemas = tool_schemas
        self.max_iterations = max_iterations
        self.memory = memory
    
    def run(self, user_input: str) -> Dict[str, Any]:
        if self.memory:
            self.memory.add_message("user", user_input)
            messages = self.memory.get_messages()
        else:
            messages = [{"role": "user", "content": user_input}]
        
        iterations = 0
        final_text = ""
        
        while iterations < self.max_iterations:
            iterations += 1
            messages, final_text, should_continue = run_agent_iteration(
                self.model, messages, self.tools_by_name, self.tool_schemas, self.prompt
            )
            
            if not should_continue:
                break
        
        if iterations >= self.max_iterations:
            final_text = "Max iterations reached."
        
        if self.memory and final_text:
            self.memory.add_message("assistant", final_text)
        
        return {"final_text": final_text, "messages": messages, "iterations": iterations}
    
    def __call__(self, user_input: str) -> Dict[str, Any]:
        return self.run(user_input)

def create_agent(
    model: LanguageModelLike,
    prompt: str = "You are a helpful assistant.",
    tools: Optional[Sequence[Union[Tool, Callable]]] = None,
    max_iterations: int = 25,
    memory: Optional[ConversationMemory] = None
):
    """Create an agent with tool-use capabilities."""
    tools_by_name, tool_schemas = prepare_tools(tools)
    
    agent = Agent(
        model=model,
        prompt=prompt,
        tools_by_name=tools_by_name,
        tool_schemas=tool_schemas,
        max_iterations=max_iterations,
        memory=memory
    )
    return agent