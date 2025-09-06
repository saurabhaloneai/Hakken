from typing import Dict, Any, Optional
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
