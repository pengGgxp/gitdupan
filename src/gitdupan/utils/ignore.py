import os
import fnmatch

def parse_ignore_file(repo_dir: str) -> list:
    """解析 .dupanignore 文件并返回一个匹配模式列表。"""
    work_dir = os.path.dirname(repo_dir)
    ignore_path = os.path.join(work_dir, ".dupanignore")
    
    patterns = [".gitdupan", ".gitdupan/*"] # 始终忽略仓库目录本身
    
    if os.path.exists(ignore_path):
        with open(ignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
                    
    return patterns

def is_ignored(rel_path: str, patterns: list) -> bool:
    """检查相对路径是否匹配任何忽略模式。"""
    # 将路径转换为使用正斜杠以实现一致的匹配
    rel_path = rel_path.replace(os.sep, "/")
    
    for pattern in patterns:
        pattern = pattern.replace(os.sep, "/")
        
        # 如果模式以 / 结尾，则匹配目录
        is_dir_pattern = pattern.endswith("/")
        if is_dir_pattern:
            pattern = pattern[:-1]
            
        # 精确匹配或者在路径中任何位置匹配
        if "/" not in pattern:
            # 例如: "*.txt" 匹配 "a/b/c.txt" 和 "c.txt"
            # 例如: "build" 匹配 "build/a" 和 "a/build/b"
            path_parts = rel_path.split("/")
            if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
                return True
        else:
            # 例如: "a/*.txt"
            if pattern.startswith("/"):
                pattern = pattern[1:]
                
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            # 同时检查它是否是该模式的子路径
            if rel_path.startswith(pattern + "/"):
                return True
                
    return False
