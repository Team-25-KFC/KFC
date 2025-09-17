import os, json, csv, shutil
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("forensic-mcp-server")


# 작업공간(샌드박스) 설정

WORKSPACE_DIR = os.path.abspath("../")   #경로 설정 지금은 ccitmcp
os.makedirs(WORKSPACE_DIR, exist_ok=True)

def _resolve_in_workspace(rel_path: str) -> str:
    """Change the relative path based on mcp-server to the absolute path, and an exception occurs when leaving"""
    rel_path = rel_path or "."
    target = os.path.abspath(os.path.join(WORKSPACE_DIR, rel_path))
    if os.path.commonpath([WORKSPACE_DIR, target]) != WORKSPACE_DIR:
        raise ValueError("Access denied: Path escapes workspace.")
    return target

def _ensure_parent_dir(path_abs: str):
    parent = os.path.dirname(path_abs) or WORKSPACE_DIR
    os.makedirs(parent, exist_ok=True)


# 유틸리티 툴

@mcp.tool()
def list_files(directory: str = ".") -> List[str]:
    """List of directories based on workspace ('.../')"""
    try:
        target = _resolve_in_workspace(directory)
        if not os.path.exists(target):
            return [f"Error: Directory '{directory}' not found."]
        if not os.path.isdir(target):
            return [f"Error: '{directory}' is not a directory."]
        return os.listdir(target)
    except Exception as e:
        return [f"An error occurred: {e}"]

@mcp.tool()
def make_dir(directory: str) -> str:
    """Create workspace reference directory (it's OK to exist)"""
    try:
        target = _resolve_in_workspace(directory)
        os.makedirs(target, exist_ok=True)
        return f"Directory ensured: '{directory}'."
    except Exception as e:
        return f"An error occurred: {e}"

@mcp.tool()
def read_file(filepath: str, encoding: str = "utf-8") -> str:
    """Read workspace reference file (director error)"""
    try:
        target = _resolve_in_workspace(filepath)
        if not os.path.exists(target):
            return f"Error: File '{filepath}' not found."
        if os.path.isdir(target):
            return f"Error: '{filepath}' is a directory, not a file."
        with open(target, "r", encoding=encoding) as f:
            return f.read()
    except Exception as e:
        return f"An error occurred: {e}"

@mcp.tool()
def write_file(filepath: str, content: str, encoding: str = "utf-8") -> str:
    """Write workspace reference file (overwrite). Reject directory path."""
    try:
        # 디렉터리로 끝나는 문자열 사전 차단
        if filepath.endswith(("/", "\\", os.path.sep)):
            return f"Error: '{filepath}' is a directory. Provide a file name."
        target = _resolve_in_workspace(filepath)
        if os.path.isdir(target):
            return f"Error: '{filepath}' is a directory. Provide a file name."
        _ensure_parent_dir(target)
        with open(target, "w", encoding=encoding) as f:
            f.write(content)
        return f"Successfully wrote to '{filepath}'."
    except Exception as e:
        return f"An error occurred: {e}"


# 삭제 툴 (파일/디렉터리)

@mcp.tool()
def delete_file(filepath: str) -> str:
    """
    Delete 'file' based on workspace. Reject if you turn over the directory.
    Workspace root self-deletion is a defense.
    """
    try:
        target = _resolve_in_workspace(filepath)
        if target == WORKSPACE_DIR:
            return "Error: Refuse to delete workspace root."
        if not os.path.exists(target):
            return f"Error: '{filepath}' does not exist."
        if os.path.isdir(target):
            return f"Error: '{filepath}' is a directory. Use delete_dir for directories."
        os.remove(target)
        return f"Deleted file: '{filepath}'."
    except Exception as e:
        return f"An error occurred: {e}"

@mcp.tool()
def delete_dir(directory: str, recursive: bool = False) -> str:
    """
    Delete 'directory' based on workspace.
    - recurrent=False: delete only when empty
    - recurrent=True: Delete the entire contents (rmtree)
    Workspace root deletion is a defense.
    """
    try:
        target = _resolve_in_workspace(directory)
        if target == WORKSPACE_DIR:
            return "Error: Refuse to delete workspace root."
        if not os.path.exists(target):
            return f"Error: '{directory}' does not exist."
        if not os.path.isdir(target):
            return f"Error: '{directory}' is not a directory."
        if recursive:
            shutil.rmtree(target)
        else:
            os.rmdir(target)  # 비어있지 않으면 OSError 발생 → 안내
        return f"Deleted directory: '{directory}'."
    except OSError as oe:
        return f"Error: Directory not empty or cannot remove without recursive=True. Detail: {oe}"
    except Exception as e:
        return f"An error occurred: {e}"


# CSV → JSON 변환 툴

@mcp.tool()
def csv_to_json(csv_file: str, json_file: str) -> str:
    """
Read CSV files and save them as JSON arrays.
    - csv_file: CSV file path based on workspace
    - json_file: converted JSON file path
    """
    try:
        csv_path = _resolve_in_workspace(csv_file)
        json_path = _resolve_in_workspace(json_file)
        _ensure_parent_dir(json_path)

        if not os.path.exists(csv_path):
            return f"Error: CSV file '{csv_file}' not found."

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

        return f"Converted '{csv_file}' → '{json_file}' ({len(rows)} rows)."
    except Exception as e:
        return f"An error occurred: {e}"
    
app = mcp.streamable_http_app()


