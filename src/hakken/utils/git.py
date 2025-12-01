import subprocess
import os
from typing import Optional, Tuple


def run_git_command(args: list[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ['git'] + args,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr or result.stdout
            
    except subprocess.TimeoutExpired:
        return False, "Git command timed out"
    except FileNotFoundError:
        return False, "Git command not found. Is git installed?"
    except Exception as e:
        return False, f"Git command failed: {e}"


def git_status(cwd: Optional[str] = None) -> Tuple[bool, str]:
    return run_git_command(['status', '--short'], cwd)


def git_diff(staged: bool = False, cwd: Optional[str] = None) -> Tuple[bool, str]:
    args = ['diff', '--staged'] if staged else ['diff']
    return run_git_command(args, cwd)


def git_log(max_count: int = 10, oneline: bool = True, cwd: Optional[str] = None) -> Tuple[bool, str]:
    args = ['log', f'-n{max_count}']
    if oneline:
        args.append('--oneline')
    return run_git_command(args, cwd)


def git_commit(message: str, cwd: Optional[str] = None) -> Tuple[bool, str]:
    if not message:
        return False, "Commit message is required"
    return run_git_command(['commit', '-m', message], cwd)


def git_add(paths: list[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
    if not paths:
        return False, "At least one path is required"
    return run_git_command(['add'] + paths, cwd)


def git_push(remote: str = 'origin', branch: Optional[str] = None, cwd: Optional[str] = None) -> Tuple[bool, str]:
    args = ['push', remote]
    if branch:
        args.append(branch)
    return run_git_command(args, cwd)


def is_git_repository(cwd: Optional[str] = None) -> bool:
    success, _ = run_git_command(['rev-parse', '--git-dir'], cwd)
    return success
