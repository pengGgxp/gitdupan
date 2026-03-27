import os
import json
import shutil
import time
from gitdupan.utils.hash import hash_file, hash_content
from gitdupan.utils.ignore import parse_ignore_file, is_ignored

def get_repo_dir(path: str = ".") -> str:
    # Find .gitdupan upwards
    curr = os.path.abspath(path)
    while True:
        repo_dir = os.path.join(curr, ".gitdupan")
        if os.path.isdir(repo_dir):
            return repo_dir
        parent = os.path.dirname(curr)
        if parent == curr:
            raise FileNotFoundError("Not a gitdupan repository (or any of the parent directories).")
        curr = parent

def init_repo(path: str = "."):
    repo_dir = os.path.join(path, ".gitdupan")
    if os.path.exists(repo_dir):
        raise FileExistsError(f"Repository already exists in {repo_dir}")
        
    os.makedirs(repo_dir)
    os.makedirs(os.path.join(repo_dir, "objects"))
    os.makedirs(os.path.join(repo_dir, "refs", "heads"))
    
    with open(os.path.join(repo_dir, "HEAD"), "w", encoding="utf-8") as f:
        f.write("ref: refs/heads/master\n")
        
    with open(os.path.join(repo_dir, "index"), "w", encoding="utf-8") as f:
        json.dump({}, f)
        
    with open(os.path.join(repo_dir, "config"), "w", encoding="utf-8") as f:
        json.dump({}, f)

def read_index(repo_dir: str) -> dict:
    with open(os.path.join(repo_dir, "index"), "r", encoding="utf-8") as f:
        return json.load(f)

def write_index(repo_dir: str, index: dict):
    with open(os.path.join(repo_dir, "index"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

def store_object(repo_dir: str, content: bytes, obj_type: str = "blob") -> str:
    """Store an object and return its hash."""
    data = json.dumps({"type": obj_type, "content": content.decode('utf-8', errors='ignore')}) if obj_type != "blob" else content
    if obj_type != "blob":
        data = data.encode('utf-8')
    
    obj_hash = hash_content(data)
    obj_path = os.path.join(repo_dir, "objects", obj_hash)
    
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(data)
            
    return obj_hash

def get_object(repo_dir: str, obj_hash: str) -> bytes:
    obj_path = os.path.join(repo_dir, "objects", obj_hash)
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"Object {obj_hash} not found")
    with open(obj_path, "rb") as f:
        return f.read()

def add_files(files: list[str]):
    repo_dir = get_repo_dir()
    index = read_index(repo_dir)
    work_dir = os.path.dirname(repo_dir)
    ignore_patterns = parse_ignore_file(repo_dir)
    
    files_to_add = []
    
    for file in files:
        if file == ".":
            # Add all non-ignored files
            for root, dirs, f_names in os.walk(work_dir):
                # Filter out ignored directories
                dirs[:] = [d for d in dirs if not is_ignored(os.path.relpath(os.path.join(root, d), work_dir), ignore_patterns)]
                for f_name in f_names:
                    full_path = os.path.join(root, f_name)
                    rel_path = os.path.relpath(full_path, work_dir)
                    if not is_ignored(rel_path, ignore_patterns):
                        files_to_add.append(full_path)
        else:
            file_path = os.path.abspath(file)
            if os.path.isdir(file_path):
                # Add directory recursively
                for root, dirs, f_names in os.walk(file_path):
                    dirs[:] = [d for d in dirs if not is_ignored(os.path.relpath(os.path.join(root, d), work_dir), ignore_patterns)]
                    for f_name in f_names:
                        full_path = os.path.join(root, f_name)
                        rel_path = os.path.relpath(full_path, work_dir)
                        if not is_ignored(rel_path, ignore_patterns):
                            files_to_add.append(full_path)
            else:
                rel_path = os.path.relpath(file_path, work_dir)
                if not is_ignored(rel_path, ignore_patterns):
                    files_to_add.append(file_path)
    
    added_count = 0
    for file_path in set(files_to_add):
        if not os.path.exists(file_path):
            continue
            
        rel_path = os.path.relpath(file_path, work_dir)
        with open(file_path, "rb") as f:
            content = f.read()
            
        obj_hash = store_object(repo_dir, content, "blob")
        index[rel_path] = {
            "type": "blob",
            "hash": obj_hash,
            "size": len(content)
        }
        added_count += 1
        
    write_index(repo_dir, index)
    return added_count

def get_current_commit(repo_dir: str) -> str:
    with open(os.path.join(repo_dir, "HEAD"), "r", encoding="utf-8") as f:
        head = f.read().strip()
    
    if head.startswith("ref: "):
        ref_path = os.path.join(repo_dir, head[5:])
        if os.path.exists(ref_path):
            with open(ref_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return None
    return head

def update_ref(repo_dir: str, ref: str, commit_hash: str):
    ref_path = os.path.join(repo_dir, ref)
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, "w", encoding="utf-8") as f:
        f.write(commit_hash)

def commit(message: str, author: str = "Unknown"):
    repo_dir = get_repo_dir()
    index = read_index(repo_dir)
    
    if not index:
        raise Exception("Nothing to commit (index is empty). Did you forget to run `gitdupan add <file>`?")
        
    # Build tree from index
    # Simple flat tree for now
    tree_content = json.dumps(index).encode('utf-8')
    tree_hash = store_object(repo_dir, tree_content, "tree")
    
    parent_commit = get_current_commit(repo_dir)
    
    commit_data = {
        "tree": tree_hash,
        "parents": [parent_commit] if parent_commit else [],
        "author": author,
        "timestamp": time.time(),
        "message": message
    }
    
    commit_content = json.dumps(commit_data).encode('utf-8')
    commit_hash = store_object(repo_dir, commit_content, "commit")
    
    # Update HEAD
    with open(os.path.join(repo_dir, "HEAD"), "r", encoding="utf-8") as f:
        head = f.read().strip()
        
    if head.startswith("ref: "):
        update_ref(repo_dir, head[5:], commit_hash)
    else:
        # Detached HEAD
        with open(os.path.join(repo_dir, "HEAD"), "w", encoding="utf-8") as f:
            f.write(commit_hash)
            
    return commit_hash

def get_log():
    repo_dir = get_repo_dir()
    commit_hash = get_current_commit(repo_dir)
    
    logs = []
    while commit_hash:
        obj_data = get_object(repo_dir, commit_hash)
        # It's JSON encoded in the object store wrapped with type info
        # Wait, my store_object saves pure bytes for blob, but wrapped JSON for tree/commit.
        # Let's decode it.
        try:
            wrapper = json.loads(obj_data.decode('utf-8'))
            commit_data = json.loads(wrapper["content"])
        except Exception:
            # fallback if saved differently
            commit_data = json.loads(obj_data.decode('utf-8'))
            
        logs.append({
            "hash": commit_hash,
            "message": commit_data.get("message", ""),
            "author": commit_data.get("author", ""),
            "timestamp": commit_data.get("timestamp", 0)
        })
        
        parents = commit_data.get("parents", [])
        commit_hash = parents[0] if parents else None
        
    return logs

def status():
    repo_dir = get_repo_dir()
    index = read_index(repo_dir)
    work_dir = os.path.dirname(repo_dir)
    
    ignore_patterns = parse_ignore_file(repo_dir)
    
    staged = list(index.keys())
    untracked = []
    modified = []
    
    for root, dirs, files in os.walk(work_dir):
        # Filter out ignored directories entirely to save time
        dirs[:] = [d for d in dirs if not is_ignored(os.path.relpath(os.path.join(root, d), work_dir), ignore_patterns)]
            
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, work_dir)
            
            # Skip ignored files
            if is_ignored(rel_path, ignore_patterns):
                continue
            
            if rel_path not in index:
                untracked.append(rel_path)
            else:
                with open(file_path, "rb") as f:
                    content = f.read()
                current_hash = hash_content(content)
                if current_hash != index[rel_path]["hash"]:
                    modified.append(rel_path)
                    
    return {"staged": staged, "modified": modified, "untracked": untracked}

def checkout(commit_hash: str, repo_dir: str = None):
    if not repo_dir:
        repo_dir = get_repo_dir()
    work_dir = os.path.dirname(repo_dir)
    
    obj_data = get_object(repo_dir, commit_hash)
    try:
        wrapper = json.loads(obj_data.decode('utf-8'))
        commit_data = json.loads(wrapper["content"])
    except Exception:
        commit_data = json.loads(obj_data.decode('utf-8'))
        
    tree_hash = commit_data["tree"]
    tree_data = get_object(repo_dir, tree_hash)
    
    try:
        tree_wrapper = json.loads(tree_data.decode('utf-8'))
        index = json.loads(tree_wrapper["content"])
    except Exception:
        index = json.loads(tree_data.decode('utf-8'))
        
    # Restore files
    for rel_path, meta in index.items():
        file_path = os.path.join(work_dir, rel_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        blob_data = get_object(repo_dir, meta["hash"])
        with open(file_path, "wb") as f:
            f.write(blob_data)
            
    # Update index and HEAD
    write_index(repo_dir, index)
    
    with open(os.path.join(repo_dir, "HEAD"), "r", encoding="utf-8") as f:
        head = f.read().strip()
        
    if head.startswith("ref: "):
        update_ref(repo_dir, head[5:], commit_hash)
    else:
        with open(os.path.join(repo_dir, "HEAD"), "w", encoding="utf-8") as f:
            f.write(commit_hash)
