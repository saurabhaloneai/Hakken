from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel

################ Pydantic Models ################

class CacheControl(BaseModel):
    type: Literal["ephemeral"] = "ephemeral"


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str
    cache_control: Optional[CacheControl] = None


class SystemMessage(BaseModel):
    role: Literal["system"] = "system"
    content: List[TextContent]


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: List[TextContent]


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[Any] = None


Message = Union[SystemMessage, UserMessage, AssistantMessage]

################ Message Builder ################

class MessageBuilder:
    
    @staticmethod
    def create_system_message(content: str) -> Dict[str, Any]:
        message = SystemMessage(content=[TextContent(text=content)])
        return message.model_dump(exclude_none=True)
    
    @staticmethod
    def create_user_message(content: str) -> Dict[str, Any]:
        message = UserMessage(content=[TextContent(text=content)])
        return message.model_dump(exclude_none=True)
    
    @staticmethod
    def create_assistant_message(
        content: Optional[str] = None, 
        tool_calls: Optional[Any] = None
    ) -> Dict[str, Any]:
        message = AssistantMessage(content=content, tool_calls=tool_calls)
        return message.model_dump(exclude_none=True)

    @staticmethod
    def apply_cache_control(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not messages:
            return messages
            
        last_message = messages[-1]
        if "content" not in last_message or not last_message["content"]:
            return messages
            
        content = last_message["content"]
        
        if isinstance(content, list) and len(content) > 0 and isinstance(content[-1], dict):
            content[-1]["cache_control"] = CacheControl().model_dump()
        elif isinstance(content, str):
            text_content = TextContent(
                text=content, 
                cache_control=CacheControl()
            )
            messages[-1]["content"] = [text_content.model_dump(exclude_none=True)]
        
        return messages

    @staticmethod
    def create_fallback_content() -> List[Dict[str, str]]:
        content = TextContent(
            text="I didn't receive any content from the model. Please provide more detail or try again."
        )
        return [content.model_dump(exclude_none=True)]
