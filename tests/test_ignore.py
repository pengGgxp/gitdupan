import os
import pytest
from gitdupan.core.repo import init_repo, add_files, status
from gitdupan.utils.ignore import parse_ignore_file, is_ignored

@pytest.fixture
def repo_env(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_ignore_logic(repo_env):
    init_repo(".")
    
    # Create a bunch of files
    os.makedirs("build")
    with open("build/temp.txt", "w") as f:
        f.write("temp")
        
    with open("test.log", "w") as f:
        f.write("log")
        
    with open("main.py", "w") as f:
        f.write("print('hello')")
        
    with open(".dupanignore", "w") as f:
        f.write("build/\n*.log\n")
        
    # Test parser directly
    patterns = parse_ignore_file(".gitdupan")
    assert "build/" in patterns
    assert "*.log" in patterns
    
    assert is_ignored("build/temp.txt", patterns) is True
    assert is_ignored("test.log", patterns) is True
    assert is_ignored("main.py", patterns) is False
    
    # Test status integration
    stat = status()
    assert "main.py" in stat["untracked"]
    assert ".dupanignore" in stat["untracked"]
    assert "test.log" not in stat["untracked"]
    assert "build/temp.txt" not in stat["untracked"]
    
    # Test add . integration
    add_count = add_files(["."])
    # Should add main.py and .dupanignore
    assert add_count == 2
    
    stat2 = status()
    assert "main.py" in stat2["staged"]
    assert ".dupanignore" in stat2["staged"]
    assert "test.log" not in stat2["staged"]
