import os
import tarfile
import json
from gitdupan.core.repo import get_repo_dir, get_object

def get_all_objects_in_commit(repo_dir: str, commit_hash: str) -> set:
    """查找可从 commit 访问的所有对象（commit, tree, blobs）。"""
    objects = set()
    if not commit_hash:
        return objects
        
    # 用于 BFS/DFS 遍历的队列
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
            # 这是一个 blob，没有进一步的引用
            pass
            
    return objects

def create_pack(repo_dir: str, target_commit: str, base_commit: str = None) -> str:
    """创建 base_commit 和 target_commit 之间增量对象的 tar.gz 压缩包。"""
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
    """将压缩包解压到 objects 目录中。"""
    with tarfile.open(pack_path, "r:gz") as tar:
        # 在较新的 Python 版本中推荐使用 filter='data' 以防止恶意的 tar 文件
        if hasattr(tarfile, 'data_filter'):
            tar.extractall(path=os.path.join(repo_dir, "objects"), filter='data')
        else:
            tar.extractall(path=os.path.join(repo_dir, "objects"))
