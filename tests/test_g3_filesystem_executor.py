from pathlib import Path
import subprocess

from jarvis.filesystem import NativeFilesystemBackend, UserPathPolicy


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


def test_create_file_bytes_absent_only(tmp_path):
    backend = NativeFilesystemBackend(UserPathPolicy((tmp_path.resolve(),)))
    target = tmp_path / "sub" / "new.txt"

    result = backend.create_file_bytes(target, b"hello\n")

    assert result.ok is True
    assert target.read_bytes() == b"hello\n"

    second = backend.create_file_bytes(target, b"changed\n")
    assert second.ok is False
    assert target.read_bytes() == b"hello\n"


def test_create_file_bytes_outside_root_blocked(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    backend = NativeFilesystemBackend(UserPathPolicy((root.resolve(),)))

    result = backend.create_file_bytes(tmp_path / "outside.txt", b"x")

    assert result.ok is False
    assert not (tmp_path / "outside.txt").exists()


def test_apply_unified_patch_authorized_target_only(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "g3@test.local")
    _git(repo, "config", "user.name", "G3")
    (repo / "a.txt").write_bytes(b"before\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "seed")

    backend = NativeFilesystemBackend(UserPathPolicy((repo.resolve(),)))
    patch = """diff --git a/a.txt b/a.txt
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-before
+after
"""

    result = backend.apply_unified_patch(repo, patch, ["a.txt"])

    assert result.ok is True
    assert (repo / "a.txt").read_bytes() == b"after\n"


def test_apply_unified_patch_target_mismatch_fails_closed(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "g3@test.local")
    _git(repo, "config", "user.name", "G3")
    (repo / "a.txt").write_text("before\n", encoding="utf-8")
    (repo / "b.txt").write_bytes(b"untouched\n")
    _git(repo, "add", "a.txt", "b.txt")
    _git(repo, "commit", "-q", "-m", "seed")

    backend = NativeFilesystemBackend(UserPathPolicy((repo.resolve(),)))
    patch = """diff --git a/a.txt b/a.txt
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-before
+after
"""

    result = backend.apply_unified_patch(repo, patch, ["b.txt"])

    assert result.ok is False
    assert (repo / "a.txt").read_bytes() == b"before\n"
    assert (repo / "b.txt").read_bytes() == b"untouched\n"
