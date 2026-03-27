import os
import tarfile
import json
from gitdupan.core.repo import get_repo_dir, get_object

def get_all_objects_in_commit(repo_dir: str, commit_hash: str) -> set:
    """Find all objects (commit, tree, blobs) reachable from a commit."""
    objects = set()
    if not commit_hash:
        return objects
        
    # Queue for BFS/DFS
    queue = [commit_hash]
    
    while queue:
        obj_hash = queue.pop(0)
        if obj_hash in objects:
            continue
            
        objects.add(obj_hash)
        
        try:
            obj_data = get_object(repo_dir, obj_hash)
            wrapper = json.loads(obj_data.decode('utf-8'))
            
            if wrapper.get("type") == "commit":
                commit_data = json.loads(wrapper["content"])
                if "tree" in commit_data:
                    queue.append(commit_data["tree"])
                for p in commit_data.get("parents", []):
                    if p:
                        queue.append(p)
                        
            elif wrapper.get("type") == "tree":
                tree_data = json.loads(wrapper["content"])
                for meta in tree_data.values():
                    if "hash" in meta:
                        queue.append(meta["hash"])
        except Exception:
            # It's a blob, no further references
            pass
            
    return objects

def create_pack(repo_dir: str, target_commit: str, base_commit: str = None) -> str:
    """Create a tar.gz pack of objects between base_commit and target_commit."""
    target_objs = get_all_objects_in_commit(repo_dir, target_commit)
    base_objs = get_all_objects_in_commit(repo_dir, base_commit) if base_commit else set()
    
    new_objs = target_objs - base_objs
    
    if not new_objs:
        return None
        
    pack_name = f"pack_{target_commit[:8]}.tar.gz"
    pack_path = os.path.join(repo_dir, "objects", pack_name)
    
    with tarfile.open(pack_path, "w:gz") as tar:
        for obj_hash in new_objs:
            obj_file = os.path.join(repo_dir, "objects", obj_hash)
            tar.add(obj_file, arcname=obj_hash)
            
    return pack_path

def unpack(repo_dir: str, pack_path: str):
    """Extract a pack file into the objects directory."""
    with tarfile.open(pack_path, "r:gz") as tar:
        # filter='data' is recommended in newer Python versions to prevent malicious tar files
        if hasattr(tarfile, 'data_filter'):
            tar.extractall(path=os.path.join(repo_dir, "objects"), filter='data')
        else:
            tar.extractall(path=os.path.join(repo_dir, "objects"))
