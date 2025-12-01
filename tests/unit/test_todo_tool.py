import pytest  # type: ignore
from hakken.tools.utilities.todo import TodoTool


class DummyUI:
    def __init__(self):
        self.items = None

    def display_todos(self, todos):
        self.items = todos


@pytest.mark.asyncio
async def test_todo_tool_updates_ui_on_write(tmp_path):
    todo_path = tmp_path / ".todos.json"
    ui = DummyUI()
    tool = TodoTool(ui_manager=ui, todo_file=str(todo_path))

    await tool.act(todos=[
        {"id": "1", "content": "Plan UI improvements", "status": "pending"}
    ])

    assert ui.items == [
        {"id": "1", "content": "Plan UI improvements", "status": "pending"}
    ]


@pytest.mark.asyncio
async def test_todo_tool_requires_todos_param(tmp_path):
    todo_path = tmp_path / ".todos.json"
    ui = DummyUI()
    tool = TodoTool(ui_manager=ui, todo_file=str(todo_path))

    result = await tool.act(todos=None)

    assert "Error" in result
    assert "required" in result


@pytest.mark.asyncio
async def test_todo_tool_validates_status(tmp_path):
    todo_path = tmp_path / ".todos.json"
    ui = DummyUI()
    tool = TodoTool(ui_manager=ui, todo_file=str(todo_path))

    result = await tool.act(todos=[
        {"id": "1", "content": "Task 1", "status": "invalid_status"}
    ])

    assert "Error" in result
    assert "invalid status" in result


@pytest.mark.asyncio
async def test_todo_tool_updates_status_to_completed(tmp_path):
    todo_path = tmp_path / ".todos.json"
    ui = DummyUI()
    tool = TodoTool(ui_manager=ui, todo_file=str(todo_path))

    # First create a pending task
    await tool.act(todos=[
        {"id": "1", "content": "Ship project cards", "status": "pending"}
    ])
    
    # Then update it to completed
    await tool.act(todos=[
        {"id": "1", "content": "Ship project cards", "status": "completed"}
    ])

    assert ui.items == [
        {"id": "1", "content": "Ship project cards", "status": "completed"}
    ]


@pytest.mark.asyncio
async def test_todo_tool_creates_md_file(tmp_path):
    todo_path = tmp_path / ".todos.json"
    md_path = tmp_path / "todo.md"
    tool = TodoTool(todo_file=str(todo_path), todo_md_file=str(md_path))

    await tool.act(todos=[
        {"id": "1", "content": "Test task", "status": "pending"}
    ])

    assert md_path.exists()
    content = md_path.read_text()
    assert "Test task" in content
    assert "Task Progress" in content


@pytest.mark.asyncio
async def test_todo_tool_removes_md_on_empty(tmp_path):
    todo_path = tmp_path / ".todos.json"
    md_path = tmp_path / "todo.md"
    tool = TodoTool(todo_file=str(todo_path), todo_md_file=str(md_path))

    # Create a task first
    await tool.act(todos=[
        {"id": "1", "content": "Test task", "status": "pending"}
    ])
    assert md_path.exists()

    # Clear all tasks
    await tool.act(todos=[])
    assert not md_path.exists()
