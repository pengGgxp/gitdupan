import json
import os
import tarfile

from gitdupan.core.repo import get_object


MAX_SPLIT_SIZE = 4 * 1024 * 1024 * 1024


def split_file(file_path: str) -> list[str]:
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

    os.remove(file_path)
    return part_paths


def merge_files(part_paths: list[str], output_path: str):
    part_paths.sort()
    with open(output_path, "wb") as f_out:
        for part_path in part_paths:
            with open(part_path, "rb") as f_in:
                while True:
                    chunk = f_in.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    f_out.write(chunk)
            os.remove(part_path)


def get_all_objects_in_commit(repo_dir: str, commit_hash: str) -> set:
    objects = set()
    if not commit_hash:
        return objects

    queue = [commit_hash]
    while queue:
        obj_hash = queue.pop(0)
        if obj_hash in objects:
            continue

        try:
            obj_data = get_object(repo_dir, obj_hash)
        except FileNotFoundError:
            continue

        objects.add(obj_hash)

        try:
            wrapper = json.loads(obj_data.decode("utf-8"))
        except Exception:
            continue

        if not isinstance(wrapper, dict):
            continue

        if wrapper.get("type") == "commit":
            commit_data = json.loads(wrapper["content"])
            if "tree" in commit_data:
                queue.append(commit_data["tree"])
            for parent in commit_data.get("parents", []):
                if parent:
                    queue.append(parent)
        elif wrapper.get("type") == "tree":
            tree_data = json.loads(wrapper["content"])
            for meta in tree_data.values():
                if meta.get("type") == "large_blob":
                    continue
                if "hash" in meta:
                    queue.append(meta["hash"])

    return objects


def create_pack(repo_dir: str, target_commit: str, base_commit: str = None) -> str:
    target_objs = get_all_objects_in_commit(repo_dir, target_commit)
    base_objs = get_all_objects_in_commit(repo_dir, base_commit) if base_commit else set()

    new_objs = target_objs - base_objs
    if not new_objs:
        return None

    pack_name = f"pack_{target_commit[:8]}.tar"
    pack_path = os.path.join(repo_dir, "objects", pack_name)

    with tarfile.open(pack_path, "w") as tar:
        for obj_hash in new_objs:
            obj_file = os.path.join(repo_dir, "objects", obj_hash)
            tar.add(obj_file, arcname=obj_hash)

    return pack_path


def unpack(repo_dir: str, pack_path: str):
    mode = "r:gz" if pack_path.endswith(".gz") else "r"
    with tarfile.open(pack_path, mode) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(path=os.path.join(repo_dir, "objects"), filter="data")
        else:
            tar.extractall(path=os.path.join(repo_dir, "objects"))
