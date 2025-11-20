"""
Simple tests for the Message system
Run with: python -m pytest test_messages.py
Or directly: python test_messages.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from python.core.message import Message, system_message, user_message, assistant_message, tool_message
from python.core.conversation import ConversationHistory
import json
import tempfile


def test_message_creation():
    """Test creating messages with helper functions"""
    print("Testing message creation...")
    
    sys_msg = system_message("You are helpful")
    assert sys_msg.role == "system"
    assert sys_msg.content == "You are helpful"
    assert isinstance(sys_msg.metadata, dict)
    
    user_msg = user_message("Hello")
    assert user_msg.role == "user"
    
    asst_msg = assistant_message("Hi there")
    assert asst_msg.role == "assistant"
    
    tool_msg = tool_message('{"result": "success"}')
    assert tool_msg.role == "tool"
    
    print("✓ Message creation tests passed")


def test_conversation_history():
    """Test ConversationHistory functionality"""
    print("Testing conversation history...")
    
    conv = ConversationHistory()
    
    # Add messages
    conv.add_system("You are a helpful assistant")
    conv.add_user("What is 2+2?")
    conv.add_assistant("2+2 equals 4")
    
    assert len(conv) == 3
    assert conv.messages[0].role == "system"
    assert conv.messages[1].role == "user"
    assert conv.messages[2].role == "assistant"
    
    print("✓ Conversation history tests passed")


def test_api_format():
    """Test conversion to API format"""
    print("Testing API format conversion...")
    
    conv = ConversationHistory()
    conv.add_user("Hello")
    conv.add_assistant("Hi!")
    
    api_msgs = conv.get_messages_for_api()
    assert len(api_msgs) == 2
    assert api_msgs[0] == {"role": "user", "content": "Hello"}
    assert api_msgs[1] == {"role": "assistant", "content": "Hi!"}
    
    print("✓ API format tests passed")


def test_filtering():
    """Test message filtering"""
    print("Testing message filtering...")
    
    conv = ConversationHistory()
    conv.add_system("System message")
    conv.add_user("User message 1")
    conv.add_assistant("Assistant message")
    conv.add_user("User message 2")
    
    user_msgs = conv.get_by_role("user")
    assert len(user_msgs) == 2
    assert all(msg.role == "user" for msg in user_msgs)
    
    last_2 = conv.get_last_n(2)
    assert len(last_2) == 2
    assert last_2[-1].content == "User message 2"
    
    print("✓ Filtering tests passed")


def test_metadata():
    """Test metadata functionality"""
    print("Testing metadata...")
    
    conv = ConversationHistory()
    conv.add_user("Search query", metadata={"intent": "search"})
    
    msg = conv.messages[0]
    assert msg.metadata["intent"] == "search"
    
    print("✓ Metadata tests passed")


def test_save_load():
    """Test saving and loading conversations"""
    print("Testing save/load...")
    
    conv1 = ConversationHistory()
    conv1.add_system("System")
    conv1.add_user("Hello")
    conv1.add_assistant("Hi!")
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
    
    try:
        conv1.save_to_file(temp_path)
        
        # Load from file
        conv2 = ConversationHistory()
        conv2.load_from_file(temp_path)
        
        assert len(conv2) == 3
        assert conv2.messages[0].content == "System"
        assert conv2.messages[1].content == "Hello"
        assert conv2.messages[2].content == "Hi!"
        
        print("✓ Save/load tests passed")
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_summary():
    """Test conversation summary"""
    print("Testing summary...")
    
    conv = ConversationHistory()
    conv.add_system("System")
    conv.add_user("User 1")
    conv.add_user("User 2")
    conv.add_assistant("Assistant")
    
    summary = conv.get_summary()
    assert summary["total_messages"] == 4
    assert summary["by_role"]["user"] == 2
    assert summary["by_role"]["assistant"] == 1
    assert summary["by_role"]["system"] == 1
    
    print("✓ Summary tests passed")


def test_max_messages():
    """Test max message limit"""
    print("Testing max messages...")
    
    conv = ConversationHistory(max_messages=5)
    conv.add_system("System message")
    
    # Add more than max
    for i in range(10):
        conv.add_user(f"User {i}")
    
    # Should keep system + 4 most recent
    assert len(conv) <= 5
    system_msgs = [m for m in conv.messages if m.role == "system"]
    assert len(system_msgs) == 1  # System message preserved
    
    print("✓ Max messages tests passed")


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Running Message System Tests")
    print("=" * 50)
    print()
    
    tests = [
        test_message_creation,
        test_conversation_history,
        test_api_format,
        test_filtering,
        test_metadata,
        test_save_load,
        test_summary,
        test_max_messages
    ]
    
    failed = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed.append(test.__name__)
    
    print()
    print("=" * 50)
    if failed:
        print(f"FAILED: {len(failed)} test(s) failed")
        for name in failed:
            print(f"  - {name}")
    else:
        print("SUCCESS: All tests passed! ✓")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
