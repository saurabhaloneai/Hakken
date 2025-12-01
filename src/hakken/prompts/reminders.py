from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hakken.tools.manager import ToolManager


def get_reminders(tool_manager: "ToolManager") -> str:
    todo_status = tool_manager.get_tool_status("todo_write")

    return f"""
<reminder>
## Current Todo Status
{todo_status}
Remember to check and update your todos using tool todo_write regularly to stay organized and productive.
</reminder>
""".strip()