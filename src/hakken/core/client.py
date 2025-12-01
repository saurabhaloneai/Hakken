import logging
from typing import Any, Dict, Generator, Tuple, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageFunctionToolCall
from openai.types.chat.chat_completion_message_function_tool_call import Function
import time 
from hakken.core.config import APIClientConfig
from hakken.utils.retry import is_retryable, retry_with_backoff

logger = logging.getLogger(__name__)

################ API Client ################

class APIClient:
    def __init__(self, config: Optional[APIClientConfig] = None):
        self.config = config or APIClientConfig()
        
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
        self._total_cost = 0
    
    @property
    def total_cost(self):
        return round(self._total_cost, 2)
    
    def get_completion(self, request_params: Dict[str, Any]) -> Tuple[Any, Any]:
        request_params["model"] = self.config.model
        
        def make_request():
            response = self.client.chat.completions.create(**request_params)
            message = response.choices[0].message
            token_usage = response.usage
            cost = getattr(token_usage, 'model_extra', {})
            if isinstance(cost, dict):
                self._total_cost += cost.get("cost", 0)
            return message, token_usage
        
        return retry_with_backoff(
            make_request,
            max_retries=self.config.max_retries,
            base_delay=self.config.base_delay,
            max_delay=self.config.max_delay,
            should_retry=is_retryable
        )
    
    def get_completion_stream(self, request_params: Dict[str, Any]) -> Generator[str, None, None]:
        request_params["model"] = self.config.model
        request_params["stream"] = True
        request_params["stream_options"] = {"include_usage": True}
        
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                yield from self._stream_completion(request_params)
                return
                
            except Exception as e:
                last_error = e
                
                if not self._is_retryable_error(e) or attempt == self.config.max_retries - 1:
                    raise Exception(f"Streaming API request failed: {str(e)}")
                
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Streaming request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
        
        raise Exception(
            f"Streaming API request failed after {self.config.max_retries} retries: {str(last_error)}"
        )
    
    def _stream_completion(self, request_params: Dict[str, Any]) -> Generator[str, None, None]:
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
            
            if chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_content += content_chunk
                yield content_chunk
            
            if hasattr(chunk.choices[0].delta, 'tool_calls') and chunk.choices[0].delta.tool_calls:
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