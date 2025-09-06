from typing import Dict, Any, Optional, Set
from dataclasses import dataclass


@dataclass
class HumanInterruptConfig:
    allow_accept: bool = True
    allow_respond: bool = True
    allow_edit: bool = False
    allow_ignore: bool = False


class InterruptConfigManager:
    
    def __init__(self):
        self._tool_configs: Dict[str, HumanInterruptConfig] = {}
        # remember approvals within this process
        self._always_allow_tools: Set[str] = set()
        self._always_allow_commands: Dict[str, Set[str]] = {}
        self._setup_default_configs()
    
    def _setup_default_configs(self):
        # Define tool name constants to avoid drift
        CMD_RUNNER = "cmd_runner"
        SMART_CONTEXT_CROPPER = "smart_context_cropper"
        DELEGATE_TASK = "delegate_task"
        WEB_SEARCH = "web_search"
        
        self._tool_configs.update({
            CMD_RUNNER: HumanInterruptConfig(
                allow_accept=True,
                allow_respond=True,
                allow_edit=True,
                allow_ignore=False
            ),
            SMART_CONTEXT_CROPPER: HumanInterruptConfig(
                allow_accept=True,
                allow_respond=True,
                allow_edit=False,
                allow_ignore=False
            ),
            DELEGATE_TASK: HumanInterruptConfig(
                allow_accept=True,
                allow_respond=True,
                allow_edit=True,
                allow_ignore=True
            ),
            WEB_SEARCH: HumanInterruptConfig(
                allow_accept=True,
                allow_respond=True,
                allow_edit=False,
                allow_ignore=False
            )
        })
    
    def get_config(self, tool_name: str) -> Optional[HumanInterruptConfig]:
        return self._tool_configs.get(tool_name)
    
    def set_config(self, tool_name: str, config: HumanInterruptConfig):
        self._tool_configs[tool_name] = config
    
    def requires_approval(self, tool_name: str, args: Dict[str, Any]) -> bool:
        # honor remembered approvals first
        if self.is_always_allowed(tool_name, args):
            return False

        config = self.get_config(tool_name)
        
        # Default approval check from args
        need_approval_from_args = args.get('need_user_approve', False)
        
        # Tools that always require approval by design
        always_require_approval = {
            'cmd_runner',  # Command execution is potentially dangerous
            'smart_context_cropper',  # Modifies conversation context
            'web_search'  # External API calls
        }
        
        return need_approval_from_args or tool_name in always_require_approval

    def is_always_allowed(self, tool_name: str, args: Dict[str, Any]) -> bool:
        # tool-level allow
        if tool_name in self._always_allow_tools:
            return True
        # command-level allow (for cmd_runner)
        if tool_name == 'cmd_runner':
            cmd = args.get('command', '') if isinstance(args, dict) else ''
            if not cmd:
                return False
            allowed = self._always_allow_commands.get(tool_name, set())
            return cmd in allowed
        return False

    def set_always_allow(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> None:
        """Remember approval for future calls. For cmd_runner, remembers the specific command string."""
        if tool_name == 'cmd_runner' and isinstance(args, dict):
            cmd = args.get('command', '')
            if cmd:
                s = self._always_allow_commands.setdefault(tool_name, set())
                s.add(cmd)
                return
        # fallback: tool-level allow
        self._always_allow_tools.add(tool_name)
    
    def get_approval_options(self, tool_name: str) -> Dict[str, bool]:
        config = self.get_config(tool_name)
        if not config:
            return {
                "allow_accept": True,
                "allow_respond": True,
                "allow_edit": False,
                "allow_ignore": False
            }
        
        return {
            "allow_accept": config.allow_accept,
            "allow_respond": config.allow_respond,
            "allow_edit": config.allow_edit,
            "allow_ignore": config.allow_ignore
        }
