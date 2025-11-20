"""
Example usage of the Message system in Hakken

This demonstrates how to use the structured Message class and ConversationHistory
for managing conversation state in your agent.
"""

from python.core.message import Message, system_message, user_message, assistant_message, tool_message
from python.core.conversation import ConversationHistory
import json

# Example 1: Creating individual messages
print("=" * 50)
print("Example 1: Creating Messages")
print("=" * 50)

# Create messages using helper functions
sys_msg = system_message("You are a helpful assistant")
user_msg = user_message("What is the weather today?")
assistant_msg = assistant_message("I'll check the weather for you.")
tool_msg = tool_message(json.dumps({"temperature": 72, "condition": "sunny"}))

print(f"System: {sys_msg.role} - {sys_msg.content}")
print(f"User: {user_msg.role} - {user_msg.content}")
print(f"Assistant: {assistant_msg.role} - {assistant_msg.content}")
print(f"Tool: {tool_msg.role} - {tool_msg.content}")
print()

# Example 2: Using ConversationHistory
print("=" * 50)
print("Example 2: Using ConversationHistory")
print("=" * 50)

# Create a conversation history
conversation = ConversationHistory(max_messages=100)

# Add messages
conversation.add_system("You are a coding assistant specializing in Python.")
conversation.add_user("How do I read a file in Python?")
conversation.add_assistant(
    "You can read a file using the built-in `open()` function. Here's an example:\n\n"
    "```python\n"
    "with open('file.txt', 'r') as f:\n"
    "    content = f.read()\n"
    "```"
)
conversation.add_user("Can you show me how to write to a file?")
conversation.add_assistant(
    "Sure! Here's how to write to a file:\n\n"
    "```python\n"
    "with open('file.txt', 'w') as f:\n"
    "    f.write('Hello, World!')\n"
    "```"
)

print(f"Total messages: {len(conversation)}")
print(f"Conversation summary: {json.dumps(conversation.get_summary(), indent=2)}")
print()

# Example 3: Getting messages for API
print("=" * 50)
print("Example 3: Converting to API Format")
print("=" * 50)

api_messages = conversation.get_messages_for_api()
print(f"API-compatible messages ({len(api_messages)} total):")
for i, msg in enumerate(api_messages[:3], 1):  # Show first 3
    print(f"{i}. {msg['role']}: {msg['content'][:50]}...")
print()

# Example 4: Filtering messages by role
print("=" * 50)
print("Example 4: Filtering Messages")
print("=" * 50)

user_messages = conversation.get_by_role("user")
print(f"User messages ({len(user_messages)} total):")
for msg in user_messages:
    print(f"  - {msg.content}")
print()

# Example 5: Adding metadata to messages
print("=" * 50)
print("Example 5: Messages with Metadata")
print("=" * 50)

conversation2 = ConversationHistory()
conversation2.add_user(
    "Search for Python tutorials", 
    metadata={"intent": "web_search", "priority": "high"}
)
conversation2.add_assistant(
    "I'll search for Python tutorials for you.",
    metadata={"tool_used": "internet_search", "search_query": "Python tutorials"}
)

for msg in conversation2.messages:
    print(f"{msg.role}: {msg.content}")
    if msg.metadata:
        print(f"  Metadata: {msg.metadata}")
print()

# Example 6: Saving and loading conversation
print("=" * 50)
print("Example 6: Save/Load Conversation")
print("=" * 50)

# Save conversation to file
save_path = "/tmp/hakken_conversation.json"
conversation.save_to_file(save_path)
print(f"Conversation saved to: {save_path}")

# Load conversation from file
loaded_conversation = ConversationHistory()
loaded_conversation.load_from_file(save_path)
print(f"Loaded conversation with {len(loaded_conversation)} messages")
print(f"Summary: {json.dumps(loaded_conversation.get_summary(), indent=2)}")
print()

# Example 7: Using with AgentLoop (demonstration)
print("=" * 50)
print("Example 7: Integration with AgentLoop")
print("=" * 50)

print("""
To use structured messages with AgentLoop, you can enable it during initialization:

```python
from python.core import AgentLoop, APIClient
from python.tools import TOOLS_DEFINITIONS, TOOL_MAPPING

client = APIClient(api_key="your-key", model_name="gpt-4")
agent = AgentLoop(
    client=client,
    tools=TOOLS_DEFINITIONS,
    tool_mapping=TOOL_MAPPING,
    model_name="gpt-4",
    use_structured_history=True  # Enable structured message history
)

# Now agent.conversation is a ConversationHistory instance
# You can save the conversation after each run:
await agent.run("Help me write a Python script")
agent.conversation.save_to_file("session_1.json")
```
""")

print("\n" + "=" * 50)
print("Examples Complete!")
print("=" * 50)
