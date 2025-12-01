import json
import os
from datetime import datetime
from typing import TYPE_CHECKING
from hakken.tools.base import BaseTool

if TYPE_CHECKING:
    from hakken.terminal_bridge import UIManager


TOOL_DESCRIPTION = """Working memory for reasoning and state tracking during complex tasks.

Use this to:
- Record reasoning steps (think) before taking action
- Store intermediate results (set/get) 
- Track your current plan (plan)
- Persist state that survives across tool calls

ReAct pattern: THINK before you ACT. Record your reasoning, then execute.

Actions:
- think: Record a reasoning step or observation
- set: Store a key-value pair 
- get: Retrieve a stored value
- delete: Remove a key
- read: View all state and recent thoughts
- clear: Reset scratchpad (optionally clear only 'thoughts' or 'state')
- plan: Set or view current plan"""


class ScratchpadTool(BaseTool):
    def __init__(self, ui_manager: "UIManager" = None, scratchpad_file=".hakken_scratchpad.json"):
        super().__init__()
        self.ui_manager = ui_manager
        self.scratchpad_file = scratchpad_file
    
    @staticmethod
    def get_tool_name():
        return "scratchpad"
    
    async def act(self, action="read", key=None, value=None, thought=None):
        try:
            pad = self._load()
            
            if action == "think":
                if not thought:
                    return "Error: thought parameter required"
                entry = {
                    "ts": datetime.now().isoformat(),
                    "thought": thought
                }
                pad["thoughts"].append(entry)
                if len(pad["thoughts"]) > 20:
                    pad["thoughts"] = pad["thoughts"][-20:]
                self._save(pad)
                return f"Recorded: {thought}"
            
            elif action == "set":
                if not key:
                    return "Error: key parameter required"
                pad["state"][key] = {
                    "value": value,
                    "updated": datetime.now().isoformat()
                }
                self._save(pad)
                return f"Set {key} = {value}"
            
            elif action == "get":
                if not key:
                    return "Error: key parameter required"
                if key not in pad["state"]:
                    return f"Key '{key}' not found"
                return json.dumps(pad["state"][key], indent=2)
            
            elif action == "delete":
                if not key:
                    return "Error: key parameter required"
                if key in pad["state"]:
                    del pad["state"][key]
                    self._save(pad)
                    return f"Deleted key '{key}'"
                return f"Key '{key}' not found"
            
            elif action == "read":
                if not pad["thoughts"] and not pad["state"]:
                    return "Scratchpad is empty"
                
                result = []
                if pad["state"]:
                    result.append("=== STATE ===")
                    for k, v in pad["state"].items():
                        result.append(f"  {k}: {v['value']}")
                
                if pad["thoughts"]:
                    result.append("\n=== RECENT THOUGHTS ===")
                    for t in pad["thoughts"][-5:]:
                        result.append(f"  [{t['ts'][:16]}] {t['thought']}")
                
                return "\n".join(result)
            
            elif action == "clear":
                section = key
                if section == "thoughts":
                    pad["thoughts"] = []
                elif section == "state":
                    pad["state"] = {}
                else:
                    pad = {"thoughts": [], "state": {}, "plan": None}
                self._save(pad)
                return f"Cleared {'all' if not section else section}"
            
            elif action == "plan":
                if thought:
                    pad["plan"] = {
                        "description": thought,
                        "created": datetime.now().isoformat()
                    }
                    self._save(pad)
                    return f"Plan set: {thought}"
                elif pad["plan"]:
                    return f"Current plan: {pad['plan']['description']}"
                return "No plan set"
            
            else:
                return f"Error: Unknown action '{action}'. Valid: think, set, get, delete, read, clear, plan"
                
        except Exception as e:
            return f"Error: {e}"
    
    def _load(self):
        if not os.path.exists(self.scratchpad_file):
            return {"thoughts": [], "state": {}, "plan": None}
        try:
            with open(self.scratchpad_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "thoughts" not in data:
                    data["thoughts"] = []
                if "state" not in data:
                    data["state"] = {}
                if "plan" not in data:
                    data["plan"] = None
                return data
        except (json.JSONDecodeError, IOError):
            return {"thoughts": [], "state": {}, "plan": None}
    
    def _save(self, pad):
        try:
            with open(self.scratchpad_file, 'w', encoding='utf-8') as f:
                json.dump(pad, f, indent=2, ensure_ascii=False)
        except IOError as e:
            pass
    
    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["think", "set", "get", "delete", "read", "clear", "plan"],
                            "default": "read"
                        },
                        "key": {
                            "type": "string",
                            "description": "Key name for set/get/delete. For clear: 'thoughts' or 'state' to clear only that section"
                        },
                        "value": {
                            "type": "string",
                            "description": "Value to store (for set action)"
                        },
                        "thought": {
                            "type": "string",
                            "description": "Reasoning step, observation, or plan description"
                        }
                    },
                    "required": []
                }
            }
        }
    
    def get_status(self):
        pad = self._load()
        thoughts = len(pad.get("thoughts", []))
        state_keys = len(pad.get("state", {}))
        has_plan = "plan" if pad.get("plan") else "no plan"
        return f"{thoughts} thoughts, {state_keys} keys, {has_plan}"
