import os
import fnmatch

def parse_ignore_file(repo_dir: str) -> list:
    """Parse .dupanignore file and return a list of patterns."""
    work_dir = os.path.dirname(repo_dir)
    ignore_path = os.path.join(work_dir, ".dupanignore")
    
    patterns = [".gitdupan", ".gitdupan/*"] # Always ignore repo dir itself
    
    if os.path.exists(ignore_path):
        with open(ignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
                    
    return patterns

def is_ignored(rel_path: str, patterns: list) -> bool:
    """Check if a relative path matches any of the ignore patterns."""
    # Convert path to use forward slashes for consistent matching
    rel_path = rel_path.replace(os.sep, "/")
    
    for pattern in patterns:
        pattern = pattern.replace(os.sep, "/")
        
        # If pattern ends with /, it matches directories
        is_dir_pattern = pattern.endswith("/")
        if is_dir_pattern:
            pattern = pattern[:-1]
            
        # Match exactly or match anywhere in the path
        if "/" not in pattern:
            # e.g. "*.txt" matches "a/b/c.txt" and "c.txt"
            # e.g. "build" matches "build/a" and "a/build/b"
            path_parts = rel_path.split("/")
            if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
                return True
        else:
            # e.g. "a/*.txt"
            if pattern.startswith("/"):
                pattern = pattern[1:]
                
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            # Also check if it's a sub-path of the pattern
            if rel_path.startswith(pattern + "/"):
                return True
                
    return False
