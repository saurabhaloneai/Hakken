from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from hakken.tools.manager import ToolManager
    from hakken.history.manager import HistoryManager
    from hakken.core.client import APIClient
    from hakken.core.config import APIClientConfig
    from hakken.prompts.manager import PromptManager
    from hakken.subagents.manager import SubagentManager
    from hakken.terminal_bridge import UIManager

################ Agent Factory ################

class AgentFactory:
    @staticmethod
    def create_tool_manager(
        history_manager: Optional["HistoryManager"] = None,
        ui_manager: Optional["UIManager"] = None,
        subagent_manager: Optional["SubagentManager"] = None
    ) -> "ToolManager":
        from hakken.tools.manager import ToolManager
        return ToolManager(
            history_manager=history_manager,
            ui_manager=ui_manager,
            subagent_manager=subagent_manager
        )
    
    @staticmethod
    def create_api_client(config: Optional["APIClientConfig"] = None) -> "APIClient":
        from hakken.core.client import APIClient
        return APIClient(config=config)
    
    @staticmethod
    def create_prompt_manager() -> "PromptManager":
        from hakken.prompts.manager import PromptManager
        return PromptManager()
    
    @staticmethod
    def create_subagent_manager() -> "SubagentManager":
        from hakken.subagents.manager import SubagentManager
        return SubagentManager()
    
    @staticmethod
    def create_history_manager(
        ui_manager: Optional["UIManager"] = None,
        api_client: Optional["APIClient"] = None,
        model_max_tokens: int = 200,
        compress_threshold: float = 0.8
    ) -> "HistoryManager":
        from hakken.history.manager import HistoryManager
        if ui_manager is None:
            raise ValueError("ui_manager must be provided for HistoryManager.")
        return HistoryManager(
            ui_manager=ui_manager,
            api_client=api_client,
            model_max_tokens=model_max_tokens,
            compress_threshold=compress_threshold
        )
    
    @staticmethod
    def create_agent(
        tool_manager: Optional["ToolManager"] = None,
        api_client: Optional["APIClient"] = None,
        ui_manager: Optional["UIManager"] = None,
        history_manager: Optional["HistoryManager"] = None,
        prompt_manager: Optional["PromptManager"] = None,
        subagent_manager: Optional["SubagentManager"] = None,
        is_bridge_mode: bool = False
    ):
        from hakken.core.agent import Agent
        
        if ui_manager is None:
            raise ValueError("ui_manager must be provided. No default implementation available.")
        
        if api_client is None:
            api_client = AgentFactory.create_api_client()
            
        if history_manager is None:
            history_manager = AgentFactory.create_history_manager(
                ui_manager=ui_manager,
                api_client=api_client
            )
            
        if tool_manager is None:
            tool_manager = AgentFactory.create_tool_manager(
                history_manager=history_manager,
                ui_manager=ui_manager,
                subagent_manager=subagent_manager
            )
            
        if prompt_manager is None:
            prompt_manager = AgentFactory.create_prompt_manager()

        if subagent_manager is None:
            subagent_manager = AgentFactory.create_subagent_manager()
        
        return Agent(
            tool_manager=tool_manager,
            api_client=api_client,
            ui_manager=ui_manager,
            history_manager=history_manager,
            prompt_manager=prompt_manager,
            subagent_manager=subagent_manager,
            is_bridge_mode=is_bridge_mode
        )