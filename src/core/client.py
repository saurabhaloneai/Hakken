from openai import OpenAI
from typing import Dict, Any, Optional, Generator, Tuple
import json
import os
from dotenv import load_dotenv
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageFunctionToolCall
from openai.types.chat.chat_completion_message_function_tool_call import Function


# Load environment variables
load_dotenv()


class APIClient:
    
    def __init__(self):
       
        self._total_cost = 0
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("OPENAI_MODEL")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        if not self.base_url:
            raise ValueError("OPENAI_BASE_URL environment variable not set")
        if not self.model:
            raise ValueError("OPENAI_MODEL environment variable not set")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    @property
    def total_cost(self):
        return round(self._total_cost, 2)
    
    def get_completion(self, request_params: Dict[str, Any]) -> Tuple[Any, Any]:
       
        params = request_params.copy()
        params["model"] = self.model
        
        params.pop("stream", None)
        params.pop("stream_options", None)
        
        try:
            response = self.client.chat.completions.create(**params)
            message = response.choices[0].message
            token_usage = response.usage
            cost = getattr(token_usage, 'model_extra', {})                                                                                  
            if isinstance(cost, dict):                                                                                                      
                self._total_cost += cost.get("cost", 0)                                                                                     
            
                
            return message, token_usage
        except Exception as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def get_completion_stream(self, request_params: Dict[str, Any]) -> Generator[str, None, None]:
       
        params = request_params.copy()
        params["model"] = self.model
        params["stream"] = True
        params["stream_options"] = {"include_usage": True}
        
        try:
            stream = self.client.chat.completions.create(**params)
            
            full_content = ""
            tool_calls = []
            current_tool_call = None
            token_usage = None
            
            for chunk in stream:
                # Handle token usage information
                if hasattr(chunk, 'usage') and chunk.usage:
                    token_usage = chunk.usage
                    cost = getattr(token_usage, 'model_extra', {})                                                                                  
                    if isinstance(cost, dict):                                                                                                      
                        self._total_cost += cost.get("cost", 0)   
                    continue
                
                if chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    full_content += content_chunk
                    yield content_chunk
                
                # Handle tool calls
                if hasattr(chunk.choices[0].delta, 'tool_calls') and chunk.choices[0].delta.tool_calls:
                    for tool_call_delta in chunk.choices[0].delta.tool_calls:
                        if tool_call_delta.index is not None:
                            # Ensure enough tool_calls slots
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
            
            
            # Convert tool_calls to OpenAI standard format
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
            
            # Return standard ChatCompletionMessage object
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

            # Add usage information to the message for tracking
            if token_usage:
                message.usage = token_usage
            
            yield message
            
        except Exception as e:
            raise Exception(f"Streaming API request failed: {str(e)}")
