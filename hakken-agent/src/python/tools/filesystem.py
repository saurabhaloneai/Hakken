import os
from pathlib import Path

class FileSystem:
    def __init__(self, workspace_root="."):
        self.root = Path(workspace_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
    
    def _resolve(self, path):
        candidate = (self.root / path).resolve()
        if str(candidate).startswith(str(self.root) + os.sep) or str(candidate) == str(self.root):
            return candidate
        return self.root
    
    def read_file(self, path, encoding='utf-8'):
        resolved = self._resolve(path)
        rel = str(resolved.relative_to(self.root)) if resolved.exists() else str(Path(path).name)
        if not resolved.exists() or resolved.is_dir():
            return {"error": "Path is not a readable file", "path": rel}
        with open(resolved, 'r', encoding=encoding) as f:
            content = f.read()
        return {"path": rel, "content": content}
    
    def write_file(self, path, content, encoding='utf-8'):
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, 'w', encoding=encoding) as f:
            f.write(content)
        return {"success": True, "path": str(resolved.relative_to(self.root))}
    
    def list_directory(self, path="."):
        resolved = self._resolve(path)
        files = []
        if resolved.is_dir():
            for item in resolved.iterdir():
                if item.is_file():
                    files.append({"path": str(item.relative_to(self.root)), "name": item.name, "size": item.stat().st_size})
        return {"files": files, "count": len(files)}
    
    def search_files(self, query, path=".", glob="text", max_file_size_kb=512, max_matches=1000):
        resolved = self._resolve(path)
        matches = []
        ignore_dirs = {'.git', 'node_modules', 'dist', 'build', 'target', '.venv', 'venv', '__pycache__', '.next', '.cache', '.idea', '.vscode'}
        text_exts = {'.html', '.htm', '.md', '.txt', '.css', '.scss', '.sass', '.js', '.jsx', '.ts', '.tsx', '.json', '.yml', '.yaml', '.py', '.rs', '.go', '.java', '.kt', '.c', '.cc', '.cpp', '.h', '.hpp'}
        
        if glob and glob != "text":
            parts = [p.strip() for p in glob.split(',') if p.strip()]
            selected_exts = set([p if p.startswith('.') else f'.{p}' for p in parts]) if parts else None
        else:
            selected_exts = text_exts
        
        for root, dirs, files in os.walk(resolved):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for name in files:
                p = Path(root) / name
                if selected_exts and p.suffix.lower() not in selected_exts:
                    continue
                if p.stat().st_size // 1024 > max_file_size_kb:
                    continue
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if query in line:
                            matches.append({'file': str(p.relative_to(self.root)), 'line_number': i, 'line': line.strip()})
                            if len(matches) >= max_matches:
                                return {"matches": matches, "count": len(matches)}
        return {"matches": matches, "count": len(matches)}
    
    def create_directory(self, path):
        resolved = self._resolve(path)
        resolved.mkdir(parents=True, exist_ok=True)
        return {"success": True, "path": str(resolved.relative_to(self.root))}
    
    def replace_in_file(self, path, find, replace, count=None, encoding='utf-8'):
        resolved = self._resolve(path)
        rel = str(resolved.relative_to(self.root)) if resolved.exists() else str(Path(path).name)
        if not resolved.exists() or resolved.is_dir():
            return {"error": "Path is not a writable file", "path": rel}
        with open(resolved, 'r', encoding=encoding) as f:
            original = f.read()
        occurrences = original.count(find)
        updated = original.replace(find, replace, count if count is not None and count >= 0 else -1)
        if updated != original:
            with open(resolved, 'w', encoding=encoding) as f:
                f.write(updated)
        return {"success": True, "path": rel, "replacements": min(occurrences, count) if count else occurrences}
    
    def get_file_info(self, path):
        resolved = self._resolve(path)
        return {
            "path": str(resolved.relative_to(self.root) if resolved.exists() else Path(path).name),
            "exists": resolved.exists(),
            "is_file": resolved.exists() and resolved.is_file(),
            "size": resolved.stat().st_size if resolved.exists() and resolved.is_file() else 0
        }

