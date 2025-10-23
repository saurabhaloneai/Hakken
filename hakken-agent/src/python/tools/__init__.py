import os
from .filesystem import FileSystem
from .environment import get_environment_info
from .internet import internet_search
from .definitions import TOOLS_DEFINITIONS

fs = FileSystem(workspace_root=os.getcwd())

TOOL_MAPPING = {
    "internet_search": internet_search,
    "read_file": fs.read_file,
    "write_file": fs.write_file,
    "list_directory": fs.list_directory,
    "create_directory": fs.create_directory,
    "search_files": fs.search_files,
    "replace_in_file": fs.replace_in_file,
    "get_file_info": fs.get_file_info,
    "get_environment_info": get_environment_info
}

__all__ = ['TOOLS_DEFINITIONS', 'TOOL_MAPPING', 'fs']

