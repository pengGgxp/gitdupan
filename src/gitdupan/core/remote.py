import os
import json
import requests
from gitdupan.core.auth import get_access_token

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
        res = requests.get(url, params=params).json()
        if "list" in res:
            return res["list"]
        return []

    def read_file(self, path: str) -> bytes:
        # Get file info to get fs_id/dlink
        url = "https://pan.baidu.com/rest/2.0/xpan/multimedia"
        params = {
            "method": "filemetas",
            "access_token": self._get_token(),
            "fsids": json.dumps([self._get_fsid(path)]),
            "dlink": 1
        }
        res = requests.get(url, params=params).json()
        
        if "list" in res and res["list"]:
            dlink = res["list"][0].get("dlink")
            if dlink:
                dlink_url = f"{dlink}&access_token={self._get_token()}"
                headers = {"User-Agent": "pan.baidu.com"}
                return requests.get(dlink_url, headers=headers).content
        return None

    def _get_fsid(self, path: str):
        # Helper to find fsid of a file by path
        parent_dir = os.path.dirname(path)
        file_name = os.path.basename(path)
        files = self.list_dir(parent_dir)
        for f in files:
            if f["server_filename"] == file_name:
                return f["fs_id"]
        raise FileNotFoundError(f"File {path} not found on remote")

    def upload_file(self, local_path: str, remote_path: str):
        # 1. Precreate
        size = os.path.getsize(local_path)
        # For simplicity, we just use a single block upload here.
        # A robust implementation would chunk the file for superfile upload.
        from gitdupan.utils.hash import hash_file
        block_list = [hash_file(local_path)] # Actually Baidu needs MD5, but we mock it or use MD5
        
        # Real Baidu API requires MD5 for blocks. 
        # Let's write a quick MD5 for Baidu.
        import hashlib
        md5 = hashlib.md5()
        with open(local_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        md5_str = md5.hexdigest()
        
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
            "block_list": json.dumps([md5_str])
        }
        res = requests.post(precreate_url, params=params, data=data).json()
        
        if "uploadid" not in res:
            # Maybe file exists and is identical
            if res.get("errno") == 0:
                return
            raise Exception(f"Precreate failed: {res}")
            
        uploadid = res["uploadid"]
        
        # 2. Upload
        upload_url = "https://d.pcs.baidu.com/rest/2.0/pcs/superfile2"
        up_params = {
            "method": "upload",
            "access_token": self._get_token(),
            "type": "tmpfile",
            "path": data["path"],
            "uploadid": uploadid,
            "partseq": 0
        }
        with open(local_path, "rb") as f:
            files = {"file": f}
            up_res = requests.post(upload_url, params=up_params, files=files).json()
            
        # 3. Create
        create_params = {
            "method": "create",
            "access_token": self._get_token()
        }
        create_data = {
            "path": data["path"],
            "size": size,
            "isdir": 0,
            "block_list": json.dumps([md5_str]),
            "uploadid": uploadid
        }
        requests.post(precreate_url, params=create_params, data=create_data)
        
    def write_file_content(self, remote_path: str, content: str):
        # A small helper to write text files like HEAD
        import tempfile
        fd, temp_path = tempfile.mkstemp()
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        self.upload_file(temp_path, remote_path)
        os.remove(temp_path)
        
    def download_file(self, remote_path: str, local_path: str):
        content = self.read_file(remote_path)
        if content:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(content)
