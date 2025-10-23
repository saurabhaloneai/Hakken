import json
import os
from pathlib import Path

class PermissionManager:
    def __init__(self):
        self.storage_path = Path(os.path.expanduser("~/.hakken/permissions.json"))
        self.permissions = {}
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                self.permissions = json.load(f)
    
    def check_permission(self, tool_name):
        perm = self.permissions.get(tool_name)
        if perm == "always":
            return True
        elif perm == "never":
            return False
        return None
    
    def set_permission(self, tool_name, always):
        self.permissions[tool_name] = "always" if always else "never"
        with open(self.storage_path, 'w') as f:
            json.dump(self.permissions, f, indent=2)

