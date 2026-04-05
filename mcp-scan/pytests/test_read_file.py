import os
from pathlib import Path
from types import SimpleNamespace

from tools.file.read_file import _is_path_allowed


def test_is_path_allowed_blocks_prefix_path_traversal(tmp_path: Path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    target_file = repo_dir / "../../../../secret.txt"

    cxt = SimpleNamespace(folder=str(repo_dir))
    # Path Traversal
    assert os.path.dirname(target_file).startswith(cxt.folder) is True
    # Preventing Path Traversal
    assert _is_path_allowed(str(target_file), cxt) is False
