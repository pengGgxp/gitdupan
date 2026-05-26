import json
import os
import tempfile

from rich.console import Console

from gitdupan.core.pack import create_pack, merge_files, split_file, unpack
from gitdupan.core.remote import BaiduPCS
from gitdupan.core.repo import (
    checkout,
    get_current_commit,
    get_large_blobs_in_commit,
    get_repo_dir,
    large_blob_matches,
)


console = Console()
LARGE_REMOTE_DIR = "large"


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


def get_large_remote_path(meta: dict) -> str:
    return f"{LARGE_REMOTE_DIR}/{meta['hash']}"


def _read_remote_head(pcs: BaiduPCS) -> str | None:
    remote_head_content = pcs.read_file("HEAD")
    if remote_head_content:
        return remote_head_content.decode("utf-8").strip()
    return None


def _upload_pack(pack_path: str, pcs: BaiduPCS):
    part_paths = split_file(pack_path)
    total_parts = len(part_paths)

    for i, part_path in enumerate(part_paths):
        part_name = os.path.basename(part_path)
        console.print(f"[cyan]Uploading pack part {i + 1}/{total_parts}: {part_name}[/cyan]")
        pcs.upload_file(part_path, f"packs/{part_name}")
        os.remove(part_path)


def _upload_large_blobs(repo_dir: str, commit_hash: str, pcs: BaiduPCS):
    work_dir = os.path.dirname(repo_dir)
    for rel_path, meta in get_large_blobs_in_commit(repo_dir, commit_hash):
        source_path = os.path.join(work_dir, rel_path)
        if not large_blob_matches(source_path, meta):
            raise Exception(
                f"Large file '{rel_path}' no longer matches the committed hash. "
                "Run `gitdupan add` and commit it again before pushing."
            )

        remote_path = get_large_remote_path(meta)
        if pcs.exists(remote_path):
            continue

        console.print(f"[cyan]Uploading large file without local object copy: {rel_path}[/cyan]")
        pcs.upload_file(source_path, remote_path)


def _download_large_blob(pcs: BaiduPCS, remote_path: str, target_path: str, meta: dict):
    if large_blob_matches(target_path, meta):
        return

    target_dir = os.path.dirname(target_path)
    os.makedirs(target_dir, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".gitdupan-large-", dir=target_dir)
    os.close(fd)

    try:
        pcs.download_file(remote_path, temp_path)
        if not large_blob_matches(temp_path, meta):
            raise Exception(f"Downloaded large object does not match expected hash: {meta['hash']}")
        os.replace(temp_path, target_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _large_blob_resolver(pcs: BaiduPCS):
    def resolve(rel_path: str, meta: dict, target_path: str):
        console.print(f"[cyan]Downloading large file: {rel_path}[/cyan]")
        _download_large_blob(pcs, get_large_remote_path(meta), target_path, meta)

    return resolve


def push():
    repo_dir = get_repo_dir()
    remote_path = get_remote(repo_dir)

    console.print("[cyan]Initializing remote connection and loading access token...[/cyan]")
    pcs = BaiduPCS(remote_path)

    local_head = get_current_commit(repo_dir)
    if not local_head:
        raise Exception("No local commit to push.")

    console.print("[cyan]Checking remote repository state...[/cyan]")
    remote_head = None
    try:
        remote_head = _read_remote_head(pcs)
    except Exception:
        pass

    if local_head == remote_head:
        return "Everything up-to-date"

    console.print("[cyan]Creating incremental pack for metadata and small objects...[/cyan]")
    pack_path = create_pack(repo_dir, target_commit=local_head, base_commit=remote_head)
    if pack_path:
        console.print("[cyan]Checking pack size and splitting when needed...[/cyan]")
        _upload_pack(pack_path, pcs)

    _upload_large_blobs(repo_dir, local_head, pcs)

    pcs.write_file_content("HEAD", local_head)
    return f"Pushed to remote {remote_path}"


def pull(repo_dir: str = None):
    if not repo_dir:
        repo_dir = get_repo_dir()

    remote_path = get_remote(repo_dir)
    pcs = BaiduPCS(remote_path)

    local_head = get_current_commit(repo_dir)

    try:
        remote_head = _read_remote_head(pcs)
    except Exception:
        raise Exception("Remote repository is empty or not accessible.")

    if local_head == remote_head:
        return "Already up-to-date"

    try:
        packs = pcs.list_dir("packs")
    except Exception:
        packs = []

    pack_groups = {}
    for pack in packs:
        filename = pack["server_filename"]
        base_name = filename.split(".part")[0] if ".part" in filename else filename
        pack_groups.setdefault(base_name, []).append(filename)

    for base_name, parts in pack_groups.items():
        parts.sort()

        downloaded_parts = []
        for part_name in parts:
            local_part = os.path.join(repo_dir, "objects", part_name)
            pcs.download_file(f"packs/{part_name}", local_part)
            downloaded_parts.append(local_part)

        local_pack = os.path.join(repo_dir, "objects", base_name)
        if len(downloaded_parts) > 1 or ".part" in downloaded_parts[0]:
            merge_files(downloaded_parts, local_pack)
        else:
            local_pack = downloaded_parts[0]

        unpack(repo_dir, local_pack)
        os.remove(local_pack)

    checkout(remote_head, repo_dir, large_resolver=_large_blob_resolver(pcs))
    return f"Pulled from remote. HEAD is now at {remote_head[:8]}"


def clone(url: str, dest: str = None):
    from gitdupan.core.repo import init_repo

    if not dest:
        dest = url.strip("/").split("/")[-1]
        if not dest:
            dest = "gitdupan-repo"

    dest_path = os.path.abspath(dest)
    if os.path.exists(dest_path) and os.listdir(dest_path):
        raise Exception(f"Target path '{dest}' exists and is not an empty directory.")

    os.makedirs(dest_path, exist_ok=True)
    init_repo(dest_path)

    repo_dir = os.path.join(dest_path, ".gitdupan")
    set_remote(url, repo_dir)

    return pull(repo_dir)
