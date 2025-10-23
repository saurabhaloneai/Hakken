TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "internet_search",
            "description": "Search the internet for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 5},
                    "topic": {"type": "string", "enum": ['general', 'news', 'finance'], "default": "general"},
                    "include_raw_content": {"type": "boolean", "default": False}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform basic calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ['add', 'subtract', 'multiply', 'divide']},
                    "num1": {"type": "number"},
                    "num2": {"type": "number"}
                },
                "required": ["operation", "num1", "num2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents from workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "encoding": {"type": "string", "default": "utf-8"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "encoding": {"type": "string", "default": "utf-8"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": "Replace occurrences of text in a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "find": {"type": "string"},
                    "replace": {"type": "string"},
                    "count": {"type": "integer", "description": "Max replacements; omit for all", "default": -1},
                    "encoding": {"type": "string", "default": "utf-8"}
                },
                "required": ["path", "find", "replace"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "Get file existence and size info",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files in directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a new directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search text in files",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "glob": {"type": "string", "description": "Comma-separated extensions, e.g. 'html,css,js'", "default": "text"},
                    "max_file_size_kb": {"type": "integer", "default": 512},
                    "max_matches": {"type": "integer", "default": 1000}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_environment_info",
            "description": "Get current environment information including working directory, git status, platform, OS version, and current date",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

