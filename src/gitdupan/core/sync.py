import os
import json
from gitdupan.core.repo import get_repo_dir, get_current_commit
from gitdupan.core.pack import create_pack, unpack
from gitdupan.core.remote import BaiduPCS

def set_remote(url: str, repo_dir: str = None):
    if not repo_dir:
        repo_dir = get_repo_dir()
        
    config_path = os.path.join(repo_dir, "config")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    config["remote"] = url
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def get_remote(repo_dir: str = None) -> str:
    if not repo_dir:
        repo_dir = get_repo_dir()
        
    config_path = os.path.join(repo_dir, "config")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    if "remote" not in config:
        raise Exception("No remote configured. Use `gitdupan remote add <path>`")
    return config["remote"]

def push():
    repo_dir = get_repo_dir()
    remote_path = get_remote(repo_dir)
    pcs = BaiduPCS(remote_path)
    
    local_head = get_current_commit(repo_dir)
    if not local_head:
        raise Exception("没有可以推送的提交 (本地无 commit)")
        
    # 获取远端 HEAD
    remote_head = None
    try:
        remote_head_content = pcs.read_file("HEAD")
        if remote_head_content:
            remote_head = remote_head_content.decode('utf-8').strip()
    except Exception:
        # 远端还没有 HEAD 文件
        pass
        
    if local_head == remote_head:
        return "Everything up-to-date"
        
    # 创建打包文件
    pack_path = create_pack(repo_dir, target_commit=local_head, base_commit=remote_head)
    
    if pack_path:
        from gitdupan.core.pack import split_file
        
        # 将 pack 文件进行分卷（如果超过 4GB 会分成多个文件）
        part_paths = split_file(pack_path)
        
        for part_path in part_paths:
            part_name = os.path.basename(part_path)
            # 上传分卷文件
            pcs.upload_file(part_path, f"packs/{part_name}")
            os.remove(part_path) # 清理本地的分卷文件
        
    # 更新远端 HEAD
    pcs.write_file_content("HEAD", local_head)
    return f"Pushed to remote {remote_path}"

def pull(repo_dir: str = None):
    if not repo_dir:
        repo_dir = get_repo_dir()
        
    remote_path = get_remote(repo_dir)
    pcs = BaiduPCS(remote_path)
    
    local_head = get_current_commit(repo_dir)
    
    # 获取远端 HEAD
    remote_head = None
    try:
        remote_head_content = pcs.read_file("HEAD")
        if remote_head_content:
            remote_head = remote_head_content.decode('utf-8').strip()
    except Exception:
        raise Exception("远程仓库为空或无法访问")
        
    if local_head == remote_head:
        return "Already up-to-date"
        
    # 下载新的打包文件
    # 在完整的实现中，我们会检查需要哪些特定的包。
    # 这里为了简单，我们列出所有包并下载缺失的。
    try:
        packs = pcs.list_dir("packs")
    except Exception:
        packs = []
    
    from gitdupan.core.pack import merge_files
    
    # 按照基础包名进行分组，处理分卷
    pack_groups = {}
    for p in packs:
        filename = p["server_filename"]
        # 处理类似 pack_xxxx.tar.gz.part000 这样的分卷名
        if ".part" in filename:
            base_name = filename.split(".part")[0]
        else:
            base_name = filename
            
        if base_name not in pack_groups:
            pack_groups[base_name] = []
        pack_groups[base_name].append(filename)
        
    for base_name, parts in pack_groups.items():
        # 如果这是一个多卷的包，确保各卷按 part 序号下载
        parts.sort()
        
        downloaded_parts = []
        for part_name in parts:
            local_part = os.path.join(repo_dir, "objects", part_name)
            pcs.download_file(f"packs/{part_name}", local_part)
            downloaded_parts.append(local_part)
            
        # 组装回原本的压缩包
        local_pack = os.path.join(repo_dir, "objects", base_name)
        if len(downloaded_parts) > 1 or ".part" in downloaded_parts[0]:
            merge_files(downloaded_parts, local_pack)
        else:
            # 单一文件，直接使用
            local_pack = downloaded_parts[0]
            
        unpack(repo_dir, local_pack)
        os.remove(local_pack)
        
    # 快进更新本地 HEAD (Fast forward)
    with open(os.path.join(repo_dir, "HEAD"), "w", encoding="utf-8") as f:
        f.write(remote_head)
        
    from gitdupan.core.repo import checkout
    checkout(remote_head, repo_dir)
    
    return f"Pulled from remote. HEAD is now at {remote_head[:8]}"

def clone(url: str, dest: str = None):
    """从远端 URL 克隆一个仓库。"""
    from gitdupan.core.repo import init_repo
    
    # 1. 确定目标目录
    if not dest:
        # 默认为 URL 的最后一部分
        dest = url.strip('/').split('/')[-1]
        if not dest:
            dest = "gitdupan-repo"
            
    dest_path = os.path.abspath(dest)
    if os.path.exists(dest_path) and os.listdir(dest_path):
        raise Exception(f"目标路径 '{dest}' 已存在且不是空目录。")
        
    os.makedirs(dest_path, exist_ok=True)
    
    # 2. 在目标目录初始化空仓库
    init_repo(dest_path)
    repo_dir = os.path.join(dest_path, ".gitdupan")
    
    # 3. 设置远程地址
    set_remote(url, repo_dir)
    
    # 4. 拉取数据
    # 临时传递 repo_dir 使得 pull/checkout 可以在指定目录下自然地工作
    return pull(repo_dir)
