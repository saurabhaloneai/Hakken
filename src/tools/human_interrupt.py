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
        self._tool_configs.update({
            "run_command": HumanInterruptConfig(
                allow_accept=True,
                allow_respond=True,
                allow_edit=True,
                allow_ignore=False
            ),
            "context_cropper": HumanInterruptConfig(
                allow_accept=True,
                allow_respond=True,
                allow_edit=False,
                allow_ignore=False
            ),
            "delegate_task": HumanInterruptConfig(
                allow_accept=True,
                allow_respond=True,
                allow_edit=True,
                allow_ignore=True
            )
        })
    
    def get_config(self, tool_name: str) -> Optional[HumanInterruptConfig]:
        return self._tool_configs.get(tool_name)
    
    def set_config(self, tool_name: str, config: HumanInterruptConfig):
        self._tool_configs[tool_name] = config
    
    def requires_approval(self, tool_name: str, args: Dict[str, Any]) -> bool:
        config = self.get_config(tool_name)
        if not config:
            return args.get('need_user_approve', False)
        
        return (args.get('need_user_approve', False) or 
                tool_name in ['run_command', 'context_cropper'])
    
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
