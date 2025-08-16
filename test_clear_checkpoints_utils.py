import os
from pathlib import Path
import checkpoints_utils

def test_clear_all_checkpoints_without_directory(tmp_path, monkeypatch):
    # point CHECKPOINT_DIR to a non-existent directory inside tmp_path
    checkpoint_dir = tmp_path / "checkpoints"
    monkeypatch.setattr(checkpoints_utils, "CHECKPOINT_DIR", str(checkpoint_dir))

    assert not checkpoint_dir.exists()
    deleted = checkpoints_utils.clear_all_checkpoints()
    assert deleted == 0
    assert not checkpoint_dir.exists(), "Function should not create directory when nothing to delete"


def test_clear_all_checkpoints_removes_files(tmp_path, monkeypatch):
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    monkeypatch.setattr(checkpoints_utils, "CHECKPOINT_DIR", str(checkpoint_dir))

    # create dummy checkpoint file
    dummy = checkpoint_dir / "sample.pkl"
    dummy.write_text("data")

    deleted = checkpoints_utils.clear_all_checkpoints()
    assert deleted == 1
    assert not dummy.exists()
    assert checkpoint_dir.exists()
