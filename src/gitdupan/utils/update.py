import os
import json
import time
import threading
import requests
from packaging import version
from rich.console import Console

from gitdupan import __version__
from gitdupan.core.auth import GLOBAL_CONFIG_DIR

console = Console()

UPDATE_FILE = os.path.join(GLOBAL_CONFIG_DIR, "update.json")
# GitHub API URL (替换为你自己的仓库地址)
GITHUB_API_URL = "https://api.github.com/repos/pengGgxp/gitdupan/releases/latest"
# 检查间隔时间：24 小时 (以秒为单位)
CHECK_INTERVAL = 24 * 60 * 60 

def get_update_info() -> dict:
    """读取本地的更新缓存文件"""
    if os.path.exists(UPDATE_FILE):
        try:
            with open(UPDATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_update_info(data: dict):
    """保存更新缓存文件"""
    if not os.path.exists(GLOBAL_CONFIG_DIR):
        os.makedirs(GLOBAL_CONFIG_DIR, exist_ok=True)
    try:
        with open(UPDATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def fetch_latest_version():
    """在后台线程中请求 GitHub API 获取最新版本号并写入缓存"""
    try:
        response = requests.get(GITHUB_API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            latest_tag = data.get("tag_name", "")
            if latest_tag.startswith("v"):
                latest_tag = latest_tag[1:] # 移除前缀 v，如 v0.1.9 -> 0.1.9
                
            info = {
                "last_check": time.time(),
                "latest_version": latest_tag,
                "download_url": data.get("html_url", "https://github.com/pengGgxp/gitdupan/releases")
            }
            save_update_info(info)
    except Exception:
        # 后台线程静默失败，不打扰用户
        pass

def check_for_updates():
    """
    检查是否有新版本。
    1. 如果缓存中的版本号大于当前版本，直接打印提示。
    2. 如果距离上次检查超过 24 小时，启动后台线程去 GitHub 拉取最新数据（不阻塞当前命令）。
    """
    info = get_update_info()
    last_check = info.get("last_check", 0)
    latest_version = info.get("latest_version", "0.0.0")
    download_url = info.get("download_url", "https://github.com/pengGgxp/gitdupan/releases")

    # 1. 判断是否需要启动后台线程刷新缓存
    if time.time() - last_check > CHECK_INTERVAL:
        thread = threading.Thread(target=fetch_latest_version, daemon=True)
        thread.start()

    # 2. 判断当前缓存里的版本是否比我本地代码的版本新
    try:
        if version.parse(latest_version) > version.parse(__version__):
            console.print(f"\n[bold yellow]💡 发现新版本 v{latest_version} (当前版本 v{__version__})！[/bold yellow]")
            console.print(f"[yellow]👉 请访问: [underline]{download_url}[/underline] 下载，或使用 `uv tool upgrade gitdupan` 升级。[/yellow]\n")
    except Exception:
        pass
