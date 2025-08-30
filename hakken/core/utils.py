"""
Utility functions for the DeepAgent system.
"""

from typing import Dict, List, Tuple, Optional, Any
from .models import Message


def split_system_and_messages(raw_messages: List[Dict]) -> Tuple[Optional[str], List[Dict]]:
    """
    Takes a list of message dicts (each having 'role' and 'content') and
    returns (system_text_or_None, filtered_messages).
    Safely handles content that is a string or a small dict like {'text': '...'}.
    """
    system_parts = []
    filtered = []
    
    for m in raw_messages:
        role = m.get("role")
        content = m.get("content")
        
        if role == "system":
            # collect multiple system messages if present
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, dict):
                # try common keys
                text = content.get("text") or content.get("content") or content.get("message") 
                if text:
                    system_parts.append(text)
            # else ignore unknown shapes
        else:
            filtered.append(m)
    
    system_text = "\n".join(system_parts) if system_parts else None
    return system_text, filtered


def compress_large_outputs(state, compression_threshold: int = 2000):
    """IMPROVEMENT 4: Compress large outputs to files, keep references"""
    for filename, content in list(state.files.items()):
        if len(content) > compression_threshold and not filename.startswith("_compressed_"):
            # Create compressed reference
            summary = content[:200] + f"... [Full content: {len(content)} chars in {filename}]"
            
            # Keep full content in file, use summary in context when needed
            compressed_filename = f"_compressed_{filename}"
            state.files[compressed_filename] = summary
            
            # Original file remains for restoration


def manage_context_memory(state, context_threshold: int = 15000):
    """IMPROVEMENT 7: Intelligent context management using file system"""
    
    # If context is getting large, compress old steps to files
    total_context_size = sum(len(msg.content) for msg in state.messages)
    
    if total_context_size > context_threshold:
        # Move old detailed results to files
        compressed_messages = []
        
        for i, msg in enumerate(state.messages):
            if len(msg.content) > 1000 and i < len(state.messages) - 3:
                # Keep recent messages, compress old ones
                summary = msg.content[:200] + f"... [Full details in message_{i}.txt]"
                state.files[f"message_{i}.txt"] = msg.content
                
                compressed_messages.append(Message(
                    role=msg.role,
                    content=summary,
                    tool_calls=msg.tool_calls
                ))
            else:
                compressed_messages.append(msg)
        
        state.messages = compressed_messages