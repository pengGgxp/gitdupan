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
    remote_path = get_remote()
    pcs = BaiduPCS(remote_path)
    
    local_head = get_current_commit(repo_dir)
    if not local_head:
        raise Exception("Nothing to push (no commits)")
        
    # Get remote HEAD
    remote_head = None
    try:
        remote_head_content = pcs.read_file("HEAD")
        if remote_head_content:
            remote_head = remote_head_content.decode('utf-8').strip()
    except Exception:
        # Remote doesn't have HEAD yet
        pass
        
    if local_head == remote_head:
        return "Everything up-to-date"
        
    # Create pack
    pack_path = create_pack(repo_dir, target_commit=local_head, base_commit=remote_head)
    
    if pack_path:
        pack_name = os.path.basename(pack_path)
        # Upload pack
        pcs.upload_file(pack_path, f"packs/{pack_name}")
        os.remove(pack_path) # Clean up local pack
        
    # Update remote HEAD
    pcs.write_file_content("HEAD", local_head)
    return f"Pushed to remote {remote_path}"

def pull(repo_dir: str = None):
    if not repo_dir:
        repo_dir = get_repo_dir()
        
    remote_path = get_remote(repo_dir)
    pcs = BaiduPCS(remote_path)
    
    local_head = get_current_commit(repo_dir)
    
    # Get remote HEAD
    remote_head = None
    try:
        remote_head_content = pcs.read_file("HEAD")
        if remote_head_content:
            remote_head = remote_head_content.decode('utf-8').strip()
    except Exception:
        raise Exception("Remote repository is empty or inaccessible")
        
    if local_head == remote_head:
        return "Already up-to-date"
        
    # Download new packs
    # In a full implementation we'd check which packs we need.
    # For now, let's list packs and download missing ones
    try:
        packs = pcs.list_dir("packs")
    except Exception:
        packs = []
    
    for p in packs:
        pack_name = p["server_filename"]
        # If we already have the target commit of this pack, we might skip it.
        # But for safety in this simple version, let's just download if it doesn't exist locally
        # or if we really need it. A better check is if the pack's commit hash is in our local repo.
        
        local_pack = os.path.join(repo_dir, "objects", pack_name)
        pcs.download_file(f"packs/{pack_name}", local_pack)
        unpack(repo_dir, local_pack)
        os.remove(local_pack)
        
    # Fast forward local HEAD
    with open(os.path.join(repo_dir, "HEAD"), "w", encoding="utf-8") as f:
        f.write(remote_head)
        
    from gitdupan.core.repo import checkout
    checkout(remote_head, repo_dir)
    
    return f"Pulled from remote. HEAD is now at {remote_head[:8]}"

def clone(url: str, dest: str = None):
    """Clone a repository from a remote URL."""
    from gitdupan.core.repo import init_repo
    
    # 1. Determine destination directory
    if not dest:
        # Default to the last part of the URL
        dest = url.strip('/').split('/')[-1]
        if not dest:
            dest = "gitdupan-repo"
            
    dest_path = os.path.abspath(dest)
    if os.path.exists(dest_path) and os.listdir(dest_path):
        raise Exception(f"Destination path '{dest}' already exists and is not an empty directory.")
        
    os.makedirs(dest_path, exist_ok=True)
    
    # 2. Init empty repo in destination
    init_repo(dest_path)
    repo_dir = os.path.join(dest_path, ".gitdupan")
    
    # 3. Set remote
    set_remote(url, repo_dir)
    
    # 4. Pull data
    # Change working directory temporarily so pull/checkout works naturally 
    # (though we modified pull to accept repo_dir, some inner functions might still use get_repo_dir if not careful)
    # Actually, we passed repo_dir to pull(), which is good.
    return pull(repo_dir)
