from pathlib import Path

import pytest

from jarvis.contracts import ActionRequest, Capability, ContextSnapshot, RiskClass
from jarvis.filesystem import NativeFilesystemBackend, UserPathPolicy
from jarvis.integrations.windows_app_inventory import AppEntry, WindowsAppInventory
from jarvis.local_actions import LocalPermissionPolicy


class Inventory(WindowsAppInventory):
    def _discover(self):
        return (
            AppEntry("Visual Studio Code", r"C:\\Tools\\Code.exe", "test"),
            AppEntry("Spotify", r"C:\\Tools\\Spotify.exe", "test"),
        )


def test_inventory_resolves_exact_and_unique_prefix():
    inventory = Inventory()
    assert inventory.resolve("spotify").target.endswith("Spotify.exe")
    assert inventory.resolve("visual studio").target.endswith("Code.exe")
    assert inventory.resolve("unknown") is None


def test_filesystem_policy_restricts_root_and_sensitive_names(tmp_path):
    policy = UserPathPolicy((tmp_path.resolve(),))
    assert policy.validate(str(tmp_path / "ok.txt")).name == "ok.txt"

    with pytest.raises(ValueError, match="outside allowed roots"):
        policy.validate(str(tmp_path.parent / "outside.txt"))

    with pytest.raises(ValueError, match="sensitive"):
        policy.validate(str(tmp_path / ".env"))


def test_filesystem_create_copy_move(tmp_path):
    backend = NativeFilesystemBackend(UserPathPolicy((tmp_path.resolve(),)))
    cap_folder = Capability("folder.create", "filesystem")
    cap_copy = Capability("file.copy", "filesystem")
    cap_move = Capability("file.move", "filesystem")

    folder = tmp_path / "new"
    assert backend.execute(ActionRequest("folder.create", {"path": str(folder)})).ok

    source = tmp_path / "source.txt"
    source.write_text("hello", encoding="utf-8")
    copied = folder / "copied.txt"
    result = backend.execute(ActionRequest("file.copy", {"source": str(source), "target": str(copied)}))
    assert result.ok and copied.read_text(encoding="utf-8") == "hello"

    moved = folder / "moved.txt"
    result = backend.execute(ActionRequest("file.move", {"source": str(copied), "target": str(moved)}))
    assert result.ok and moved.exists() and not copied.exists()


def test_delete_is_blocked_by_default_permission_policy():
    policy = LocalPermissionPolicy()
    request = ActionRequest("file.delete", {"path": "x"}, risk=RiskClass.DESTRUCTIVE)
    assert policy.evaluate(request, ContextSnapshot("test")).value == "ask"
