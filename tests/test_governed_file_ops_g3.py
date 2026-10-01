from pathlib import Path
from unittest.mock import MagicMock

from jarvis.governed_file_ops import (
    GovernedApplyPatchCoordinator,
    GovernedCreateFileCoordinator,
    GovernedFileOpsCommandHandler,
    GovernedFileOpsConfig,
)


def _config(tmp_path: Path) -> GovernedFileOpsConfig:
    return GovernedFileOpsConfig(
        execution_worktree_path=tmp_path / "exec",
        main_worktree_path=tmp_path / "main",
        branch_name="g3",
        base_sha="abc123",
        stores_base_dir=tmp_path / "stores",
        obsidia_root=tmp_path / "obsidia",
    )


def test_create_file_prepare_is_non_mutating(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "a" * 64,
    }
    execute = MagicMock()
    factory = MagicMock()
    c = GovernedCreateFileCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        factory,
    )

    reply = c.prepare("new.txt", b"hello", session_id="s1")

    assert "préparée" in reply
    assert c.pending is prepared
    execute.assert_not_called()
    factory.assert_not_called()


def test_create_file_confirm_executes_once(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "b" * 64,
    }
    execute = MagicMock(return_value={"status": "EXECUTED_OK", "target_path": "new.txt"})
    executor = object()
    c = GovernedCreateFileCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(return_value=executor),
    )

    c.prepare("new.txt", b"hello", session_id="s1")
    reply = c.approve(session_id="s1")

    assert "créé et prouvé" in reply
    assert c.pending is None
    _, kwargs = execute.call_args
    assert kwargs["executor"] is executor


def test_create_file_failure_keeps_pending(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "c" * 64,
    }
    c = GovernedCreateFileCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        MagicMock(return_value={"status": "EXECUTE_REJECTED", "reason": "KX108_PRE_GATE:BLOCK"}),
        MagicMock(return_value=object()),
    )

    c.prepare("new.txt", b"hello", session_id="s1")
    reply = c.approve(session_id="s1")

    assert "KX108_PRE_GATE:BLOCK" in reply
    assert c.pending is prepared


def test_patch_prepare_is_non_mutating(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "d" * 64,
        "target_paths": ["a.txt"],
    }
    execute = MagicMock()
    c = GovernedApplyPatchCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(),
    )

    reply = c.prepare("diff", session_id="s1")

    assert "Patch préparé" in reply
    assert c.pending is prepared
    execute.assert_not_called()


def test_patch_confirm_executes_once(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "e" * 64,
        "target_paths": ["a.txt"],
    }
    execute = MagicMock(return_value={"status": "EXECUTED_OK", "target_paths": ["a.txt"]})
    executor = object()
    c = GovernedApplyPatchCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(return_value=executor),
    )

    c.prepare("diff", session_id="s1")
    reply = c.approve(session_id="s1")

    assert "appliqué et prouvé" in reply
    assert c.pending is None
    _, kwargs = execute.call_args
    assert kwargs["executor"] is executor


def test_patch_failure_keeps_pending(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "f" * 64,
        "target_paths": ["a.txt"],
    }
    c = GovernedApplyPatchCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        MagicMock(return_value={"status": "EXECUTE_REJECTED", "reason": "KX108_PRE_GATE:BLOCK"}),
        MagicMock(return_value=object()),
    )

    c.prepare("diff", session_id="s1")
    reply = c.approve(session_id="s1")

    assert "KX108_PRE_GATE:BLOCK" in reply
    assert c.pending is prepared


def test_text_create_file_two_phase(tmp_path):
    create_prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "1" * 64,
    }
    create_execute = MagicMock(return_value={"status": "EXECUTED_OK", "target_path": "notes/a.txt"})
    create = GovernedCreateFileCoordinator(
        _config(tmp_path),
        MagicMock(return_value=create_prepared),
        create_execute,
        MagicMock(return_value=object()),
    )
    patch = GovernedApplyPatchCoordinator(_config(tmp_path), MagicMock(), MagicMock(), MagicMock())
    h = GovernedFileOpsCommandHandler(create, patch)

    first = h.handle("cree le fichier notes/a.txt avec contenu bonjour", session_id="hud")
    assert first is not None and "préparée" in first
    create_execute.assert_not_called()

    second = h.handle("confirme la creation du fichier", session_id="hud")
    assert second is not None and "créé" in second
    create_execute.assert_called_once()


def test_text_patch_two_phase(tmp_path):
    patch_text = """diff --git a/a.txt b/a.txt
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-before
+after
"""
    patch_prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "2" * 64,
        "target_paths": ["a.txt"],
    }
    patch_execute = MagicMock(return_value={"status": "EXECUTED_OK", "target_paths": ["a.txt"]})
    create = GovernedCreateFileCoordinator(_config(tmp_path), MagicMock(), MagicMock(), MagicMock())
    patch = GovernedApplyPatchCoordinator(
        _config(tmp_path),
        MagicMock(return_value=patch_prepared),
        patch_execute,
        MagicMock(return_value=object()),
    )
    h = GovernedFileOpsCommandHandler(create, patch)

    first = h.handle("applique le patch\n" + patch_text, session_id="hud")
    assert first is not None and "Patch préparé" in first
    patch_execute.assert_not_called()

    second = h.handle("confirme le patch", session_id="hud")
    assert second is not None and "appliqué" in second
    patch_execute.assert_called_once()


def test_unrelated_text_is_ignored(tmp_path):
    h = GovernedFileOpsCommandHandler(
        GovernedCreateFileCoordinator(_config(tmp_path), MagicMock(), MagicMock(), MagicMock()),
        GovernedApplyPatchCoordinator(_config(tmp_path), MagicMock(), MagicMock(), MagicMock()),
    )
    assert h.handle("explique Obsidia", session_id="s1") is None
