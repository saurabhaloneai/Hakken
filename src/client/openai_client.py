from openai import OpenAI
from typing import Dict, Any, Generator, Tuple
import os
from dotenv import load_dotenv
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageFunctionToolCall
from openai.types.chat.chat_completion_message_function_tool_call import Function
from dataclasses import dataclass

load_dotenv()


@dataclass
class APIConfiguration:
    api_key: str
    base_url: str
    model: str
    
    @classmethod
    def from_environment(cls) -> 'APIConfiguration':
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        if not base_url:
            raise ValueError("OPENAI_BASE_URL environment variable not set")
        if not model:
            raise ValueError("OPENAI_MODEL environment variable not set")
            
        return cls(api_key=api_key, base_url=base_url, model=model)


class APIClient:
    
    def __init__(self, config: APIConfiguration):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        self._total_cost = 0.0
    
    @property
    def total_cost(self) -> float:
        return round(self._total_cost, 2)
    
    def get_completion(self, request_params: Dict[str, Any]) -> Tuple[Any, Any]:
        request_params["model"] = self.config.model
        try:
            response = self.client.chat.completions.create(**request_params)
            message = response.choices[0].message
            token_usage = response.usage
            
            cost = getattr(token_usage, 'model_extra', {})
            if isinstance(cost, dict):
                self._total_cost += cost.get("cost", 0)
                
            return message, token_usage
        except Exception as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def get_completion_stream(self, request_params: Dict[str, Any]) -> Generator[str, None, None]:
        request_params["model"] = self.config.model
        request_params["stream"] = True
        request_params["stream_options"] = {"include_usage": True}
        
        try:
            stream = self.client.chat.completions.create(**request_params)
            
            full_content = ""
            tool_calls = []
            current_tool_call = None
            token_usage = None
            
            for chunk in stream:
                if hasattr(chunk, 'usage') and chunk.usage:
                    token_usage = chunk.usage
                    cost = getattr(token_usage, 'model_extra', {})
                    if isinstance(cost, dict):
                        self._total_cost += cost.get("cost", 0)
                    continue
                
                if (hasattr(chunk, 'choices') and 
                    len(chunk.choices) > 0 and 
                    hasattr(chunk.choices[0], 'delta') and 
                    hasattr(chunk.choices[0].delta, 'content') and 
                    chunk.choices[0].delta.content):
                    
                    content_chunk = chunk.choices[0].delta.content
                    full_content += content_chunk
                    yield content_chunk
                
                if (hasattr(chunk, 'choices') and 
                    len(chunk.choices) > 0 and 
                    hasattr(chunk.choices[0], 'delta') and
                    hasattr(chunk.choices[0].delta, 'tool_calls') and 
                    chunk.choices[0].delta.tool_calls):
                    
                    for tool_call_delta in chunk.choices[0].delta.tool_calls:
                        if tool_call_delta.index is not None:
                            while len(tool_calls) <= tool_call_delta.index:
                                tool_calls.append({
                                    'id': None,
                                    'type': 'function',
                                    'function': {'name': None, 'arguments': ''}
                                })
                            
                            current_tool_call = tool_calls[tool_call_delta.index]
                            
                            if tool_call_delta.id:
                                current_tool_call['id'] = tool_call_delta.id
                            
                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    current_tool_call['function']['name'] = tool_call_delta.function.name
                                if tool_call_delta.function.arguments:
                                    current_tool_call['function']['arguments'] += tool_call_delta.function.arguments
            
            formatted_tool_calls = None
            if tool_calls and any(tc['id'] for tc in tool_calls):
                formatted_tool_calls = []
                for tc in tool_calls:
                    if tc['id'] and tc['function']['name']:
                        formatted_tool_calls.append(
                            ChatCompletionMessageFunctionToolCall(
                                id=tc['id'],
                                function=Function(
                                    name=tc['function']['name'],
                                    arguments=tc['function']['arguments']
                                ),
                                type='function'
                            )
                        )
            
            message = ChatCompletionMessage(
                content=full_content,
                role="assistant",
                tool_calls=formatted_tool_calls,
                refusal=None,
                annotations=None,
                audio=None,
                function_call=None,
                reasoning=None
            )

            if token_usage:
                message.usage = token_usage
            
            yield message
            
        except Exception as e:
            raise Exception(f"Streaming API request failed: {str(e)}")
