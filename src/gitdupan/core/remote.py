import os
import json
import requests
import hashlib
import time
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from gitdupan.core.auth import get_access_token

CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks for Baidu PCS

def _retry_request(method, url, max_retries=3, **kwargs):
    """Helper to retry requests on connection errors."""
    for attempt in range(max_retries):
        try:
            return method(url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

class BaiduPCS:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir.rstrip('/')
        
    def _get_token(self):
        return get_access_token()
        
    def list_dir(self, path: str):
        url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {
            "method": "list",
            "access_token": self._get_token(),
            "dir": f"{self.base_dir}/{path.lstrip('/')}"
        }
        res = _retry_request(requests.get, url, params=params, timeout=10).json()
        if "list" in res:
            return res["list"]
        return []

    def get_download_link(self, path: str) -> str:
        """Get the dlink for a file."""
        url = "https://pan.baidu.com/rest/2.0/xpan/multimedia"
        params = {
            "method": "filemetas",
            "access_token": self._get_token(),
            "fsids": json.dumps([self._get_fsid(path)]),
            "dlink": 1
        }
        res = _retry_request(requests.get, url, params=params, timeout=10).json()
        
        if "list" in res and res["list"]:
            dlink = res["list"][0].get("dlink")
            if dlink:
                return f"{dlink}&access_token={self._get_token()}"
        return None

    def read_file(self, path: str) -> bytes:
        dlink_url = self.get_download_link(path)
        if dlink_url:
            headers = {"User-Agent": "pan.baidu.com"}
            return _retry_request(requests.get, dlink_url, headers=headers, timeout=30).content
        return None

    def download_file(self, remote_path: str, local_path: str):
        """Streaming download for large files."""
        dlink_url = self.get_download_link(remote_path)
        if not dlink_url:
            raise Exception(f"Could not get download link for {remote_path}")
            
        headers = {"User-Agent": "pan.baidu.com"}
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Use streaming to avoid loading huge files into memory
        with _retry_request(requests.get, dlink_url, headers=headers, stream=True, timeout=15) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.0f}%",
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn()
            ) as progress:
                filename = os.path.basename(local_path)
                task_id = progress.add_task(f"Downloading {filename}", total=total_size)
                
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            progress.update(task_id, advance=len(chunk))

    def _get_fsid(self, path: str):
        parent_dir = os.path.dirname(path)
        file_name = os.path.basename(path)
        files = self.list_dir(parent_dir)
        for f in files:
            if f["server_filename"] == file_name:
                return f["fs_id"]
        raise FileNotFoundError(f"File {path} not found on remote")

    def _calculate_block_list(self, local_path: str) -> list[str]:
        """Calculate MD5 for each chunk of the file."""
        block_list = []
        with open(local_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                md5 = hashlib.md5()
                md5.update(chunk)
                block_list.append(md5.hexdigest())
        return block_list

    def upload_file(self, local_path: str, remote_path: str):
        size = os.path.getsize(local_path)
        block_list = self._calculate_block_list(local_path)
        
        # 1. Precreate
        precreate_url = "https://pan.baidu.com/rest/2.0/xpan/file"
        params = {
            "method": "precreate",
            "access_token": self._get_token()
        }
        data = {
            "path": f"{self.base_dir}/{remote_path.lstrip('/')}",
            "size": size,
            "isdir": 0,
            "autoinit": 1,
            "block_list": json.dumps(block_list)
        }
        res = _retry_request(requests.post, precreate_url, params=params, data=data, timeout=10).json()
        
        if "uploadid" not in res:
            if res.get("errno") == 0 or res.get("errno") == 40748: # 40748 = file already exists
                return # File might be identical or rapidly uploaded
            raise Exception(f"Precreate failed: {res}")
            
        uploadid = res["uploadid"]
        
        # 2. Upload chunks sequentially
        upload_url = "https://d.pcs.baidu.com/rest/2.0/pcs/superfile2"
        filename = os.path.basename(local_path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn()
        ) as progress:
            task_id = progress.add_task(f"Uploading {filename}", total=size)
            
            with open(local_path, "rb") as f:
                for partseq, _ in enumerate(block_list):
                    chunk_data = f.read(CHUNK_SIZE)
                    if not chunk_data:
                        break
                        
                    up_params = {
                        "method": "upload",
                        "access_token": self._get_token(),
                        "type": "tmpfile",
                        "path": data["path"],
                        "uploadid": uploadid,
                        "partseq": partseq
                    }
                    
                    files = {"file": ("chunk", chunk_data)}
                    up_res = _retry_request(requests.post, upload_url, params=up_params, files=files, timeout=60).json()
                    if "md5" not in up_res:
                        raise Exception(f"Chunk upload failed at part {partseq}: {up_res}")
                        
                    progress.update(task_id, advance=len(chunk_data))
            
        # 3. Create (Merge)
        create_params = {
            "method": "create",
            "access_token": self._get_token()
        }
        create_data = {
            "path": data["path"],
            "size": size,
            "isdir": 0,
            "block_list": json.dumps(block_list),
            "uploadid": uploadid
        }
        _retry_request(requests.post, precreate_url, params=create_params, data=create_data, timeout=10)
        
    def write_file_content(self, remote_path: str, content: str):
        import tempfile
        fd, temp_path = tempfile.mkstemp()
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        self.upload_file(temp_path, remote_path)
        os.remove(temp_path)
