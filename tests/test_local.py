import os
import shutil
import pytest
from gitdupan.core.repo import init_repo, add_files, commit, get_log, status, checkout
from gitdupan.core.pack import create_pack, unpack

@pytest.fixture
def repo_env(tmp_path):
    # Change current working directory to a temporary path
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_local_workflow(repo_env):
    # Init
    init_repo(".")
    assert os.path.exists(".gitdupan")
    
    # Create file
    with open("a.txt", "w") as f:
        f.write("v1")
        
    # Status
    stat = status()
    assert "a.txt" in stat["untracked"]
    
    # Add
    add_files(["a.txt"])
    stat = status()
    assert "a.txt" in stat["staged"]
    
    # Commit
    c1 = commit("First commit")
    assert c1 is not None
    
    # Modify
    with open("a.txt", "w") as f:
        f.write("v2")
    
    stat = status()
    assert "a.txt" in stat["modified"]
    
    # Add & Commit
    add_files(["a.txt"])
    c2 = commit("Second commit")
    
    # Log
    logs = get_log()
    assert len(logs) == 2
    assert logs[0]["hash"] == c2
    assert logs[1]["hash"] == c1
    
    # Checkout
    checkout(c1)
    with open("a.txt", "r") as f:
        content = f.read()
    assert content == "v1"

def test_pack_workflow(repo_env):
    init_repo(".")
    with open("b.txt", "w") as f:
        f.write("test pack")
    add_files(["b.txt"])
    c1 = commit("pack test")
    
    # Pack
    pack_file = create_pack(".gitdupan", c1)
    assert pack_file is not None
    assert os.path.exists(pack_file)
    
    # Unpack test (mock a new repo)
    repo2 = repo_env / "repo2"
    os.makedirs(repo2)
    
    # Use absolute path before changing directory
    abs_pack_file = os.path.abspath(pack_file)
    
    os.chdir(repo2)
    init_repo(".")
    
    shutil.copy(abs_pack_file, ".gitdupan/objects/")
    unpack(".gitdupan", os.path.join(".gitdupan/objects/", os.path.basename(abs_pack_file)))
    
    checkout(c1)
    with open("b.txt", "r") as f:
        content = f.read()
    assert content == "test pack"
