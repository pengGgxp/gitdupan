import hashlib
import os

def hash_file(file_path: str) -> str:
    """计算文件的 SHA-256 哈希值。"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def hash_content(content: bytes) -> str:
    """计算字节内容的 SHA-256 哈希值。"""
    sha256 = hashlib.sha256()
    sha256.update(content)
    return sha256.hexdigest()
