import os
import pytest
from unittest.mock import patch
from gitdupan.core.repo import init_repo, add_files, commit, read_index
from gitdupan.core.sync import set_remote, push, pull

@pytest.fixture
def repo_env(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_sync_workflow(repo_env):
    init_repo(".")
    with open("c.txt", "w") as f:
        f.write("test sync")
    add_files(["c.txt"])
    c1 = commit("sync commit")
    
    set_remote("/apps/gitdupan/testrepo")
    
    # Mock BaiduPCS
    with patch("gitdupan.core.sync.BaiduPCS") as MockPCS:
        pcs_instance = MockPCS.return_value
        
        # 1. Test Push
        # remote has no HEAD
        pcs_instance.read_file.side_effect = Exception("Not found")
        
        res = push()
        assert "Pushed to remote" in res
        
        # Verify it created a pack and uploaded
        pcs_instance.upload_file.assert_called_once()
        pcs_instance.write_file_content.assert_called_once_with("HEAD", c1)
        
        # 2. Test Pull
        # mock remote HEAD exists
        pcs_instance.read_file.side_effect = None
        pcs_instance.read_file.return_value = c1.encode('utf-8')
        
        res = pull()
        assert "Already up-to-date" in res

def test_push_uploads_large_blob_from_worktree(repo_env, monkeypatch):
    monkeypatch.setenv("GITDUPAN_LARGE_FILE_THRESHOLD", "4")
    init_repo(".")
    with open("large.bin", "wb") as f:
        f.write(b"0123456789")
    add_files(["large.bin"])
    c1 = commit("large sync commit")
    meta = read_index(".gitdupan")["large.bin"]

    set_remote("/apps/gitdupan/testrepo")

    with patch("gitdupan.core.sync.BaiduPCS") as MockPCS:
        pcs_instance = MockPCS.return_value
        pcs_instance.read_file.side_effect = Exception("Not found")
        pcs_instance.exists.return_value = False

        res = push()
        assert "Pushed to remote" in res

        upload_targets = [call.args[1] for call in pcs_instance.upload_file.call_args_list]
        assert any(target.startswith("packs/") for target in upload_targets)
        assert f"large/{meta['hash']}" in upload_targets
        assert not os.path.exists(os.path.join(".gitdupan", "objects", meta["hash"]))
        pcs_instance.write_file_content.assert_called_once_with("HEAD", c1)
