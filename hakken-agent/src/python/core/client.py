from typing import List, Dict, Any, Optional, Callable
from openai import OpenAI
from openai.types.chat import ChatCompletion
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

class APIClient:
    def __init__(self, api_key: str, model_name: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.stop_event = None
        
        def is_float(s: str) -> bool:
            return s.replace('.', '', 1).isdigit()
        
        def parse_int_with_suffix(value: str, default_value: int, hard_ceil: int) -> int:
            v = value.strip().lower()
            mult = 1000 if v.endswith('k') else 1000000 if v.endswith('m') else 1
            v = v[:-1] if mult > 1 else v
            n = int(v) * mult if v.isdigit() else default_value
            return max(1, min(n, hard_ceil))
        
        max_tokens_env = os.getenv("HAKKEN_MAX_TOKENS")
        temperature_env = os.getenv("HAKKEN_TEMPERATURE")
        self.max_tokens = parse_int_with_suffix(max_tokens_env, 4000, 128000) if max_tokens_env else 40000
        self.temperature = float(temperature_env) if (temperature_env and is_float(temperature_env)) else 0.2
    
    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        on_content_chunk: Optional[Callable[[str], None]] = None
    ) -> tuple[str, List[Dict[str, Any]]]:
        request = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **({"tools": tools} if tools else {})
        }
        
        completion: ChatCompletion = self.client.chat.completions.create(**request)
        tool_calls: Dict[int, Dict[str, Any]] = {}
        content = ""
        
        for chunk in completion:
            if self.stop_event and self.stop_event.is_set():
                completion.close()
                raise asyncio.CancelledError("Stop requested")
            
            delta = chunk.choices[0].delta
            
            if delta.content:
                content += delta.content
                if on_content_chunk:
                    on_content_chunk(delta.content)
            
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            'id': tc_delta.id or f"call_{idx}",
                            'type': tc_delta.type or 'function',
                            'function': {'name': '', 'arguments': ''}
                        }
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls[idx]['function']['name'] = tc_delta.function.name
                        tool_calls[idx]['function']['arguments'] += tc_delta.function.arguments or ''
            
            await asyncio.sleep(0)
        
        return content, [tool_calls[idx] for idx in sorted(tool_calls.keys())]
