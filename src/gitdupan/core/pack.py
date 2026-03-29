import os
import tarfile
import json
from gitdupan.core.repo import get_repo_dir, get_object

# 最大分卷大小，设置为 4GB (单位：字节)
MAX_SPLIT_SIZE = 4 * 1024 * 1024 * 1024

def split_file(file_path: str) -> list[str]:
    """将大文件按 MAX_SPLIT_SIZE 切割成多个分卷，返回分卷路径列表。"""
    file_size = os.path.getsize(file_path)
    if file_size <= MAX_SPLIT_SIZE:
        return [file_path]
        
    part_paths = []
    part_num = 0
    with open(file_path, "rb") as f_in:
        while True:
            chunk = f_in.read(MAX_SPLIT_SIZE)
            if not chunk:
                break
            part_path = f"{file_path}.part{part_num:03d}"
            with open(part_path, "wb") as f_out:
                f_out.write(chunk)
            part_paths.append(part_path)
            part_num += 1
            
    # 切割完成后删除原文件，释放空间
    os.remove(file_path)
    return part_paths

def merge_files(part_paths: list[str], output_path: str):
    """将多个分卷合并为一个完整的文件。"""
    # 确保分卷按序号排序
    part_paths.sort()
    with open(output_path, "wb") as f_out:
        for part_path in part_paths:
            with open(part_path, "rb") as f_in:
                # 使用固定大小的缓冲区以节省内存
                while True:
                    chunk = f_in.read(8 * 1024 * 1024) # 8MB
                    if not chunk:
                        break
                    f_out.write(chunk)
            # 合并完成后删除分卷文件
            os.remove(part_path)

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
