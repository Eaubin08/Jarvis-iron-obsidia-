"""Jarjar-owned filesystem actions with bounded path policy.

The path-policy shape is adapted from OpenJarvis' Apache-2.0 file tools:
resolve paths, restrict roots when configured, and block sensitive filenames.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import subprocess

from .contracts import ActionRequest, ActionResult, Capability


_SENSITIVE_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service_account.json",
}
_SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


@dataclass
class UserPathPolicy:
    allowed_roots: tuple[Path, ...] = field(default_factory=tuple)

    @classmethod
    def default(cls) -> "UserPathPolicy":
        home = Path.home().resolve()
        return cls((home,))

    def validate(self, raw: str, *, must_exist: bool = False) -> Path:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("missing filesystem path")
        path = Path(os.path.expandvars(os.path.expanduser(raw.strip()))).resolve(strict=False)

        name = path.name.casefold()
        if name in _SENSITIVE_NAMES or path.suffix.casefold() in _SENSITIVE_SUFFIXES:
            raise ValueError(f"sensitive filesystem path blocked: {path.name}")
        if any(part.casefold() == ".ssh" for part in path.parts):
            raise ValueError("sensitive filesystem path blocked: .ssh")

        if self.allowed_roots and not any(
            path == root or path.is_relative_to(root) for root in self.allowed_roots
        ):
            raise ValueError("filesystem path is outside allowed roots")
        if must_exist and not path.exists():
            raise ValueError(f"filesystem path not found: {path}")
        return path


@dataclass
class NativeFilesystemBackend:
    policy: UserPathPolicy = field(default_factory=UserPathPolicy.default)
    name: str = "filesystem.structured"
    priority: int = 12

    _supported = frozenset({
        "file.open",
        "file.reveal",
        "folder.create",
        "file.copy",
        "file.move",
        "file.delete",
    })

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        return capability.backend_family == "filesystem" and request.capability in self._supported

    def create_file_bytes(self, target: str | Path, content: bytes) -> ActionResult:
        try:
            path = self.policy.validate(str(target))
            if path.exists():
                return ActionResult(False, "target already exists", backend=self.name)
            if not isinstance(content, (bytes, bytearray)):
                return ActionResult(False, "content must be bytes", backend=self.name)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.parent / f".{path.name}.{os.getpid()}.jarjar.tmp"
            tmp.write_bytes(bytes(content))
            os.replace(tmp, path)
            return ActionResult(
                True,
                "Filesystem action completed",
                data={"path": str(path), "bytes": len(content)},
                backend=self.name,
            )
        except (OSError, ValueError) as exc:
            return ActionResult(False, str(exc), backend=self.name)

    def apply_unified_patch(
        self,
        repo_root: str | Path,
        patch_content: str,
        target_paths: list[str] | tuple[str, ...],
    ) -> ActionResult:
        try:
            root = self.policy.validate(str(repo_root), must_exist=True)
            if not root.is_dir():
                return ActionResult(False, "repo root is not a directory", backend=self.name)
            if not isinstance(patch_content, str) or not patch_content.strip():
                return ActionResult(False, "patch content must be non-empty text", backend=self.name)
            if not target_paths:
                return ActionResult(False, "patch target list must not be empty", backend=self.name)

            expected = []
            for rel in target_paths:
                if not isinstance(rel, str) or not rel.strip():
                    return ActionResult(False, "invalid patch target", backend=self.name)
                target = self.policy.validate(str(root / rel), must_exist=True)
                expected.append(str(target.relative_to(root)).replace("\\", "/"))

            parsed = []
            for line in patch_content.splitlines():
                if not line.startswith("+++ "):
                    continue
                raw = line[4:].strip()
                if raw.startswith("b/"):
                    raw = raw[2:]
                if raw in {"/dev/null", "dev/null"}:
                    return ActionResult(False, "patch deletion is not allowed", backend=self.name)
                candidate = self.policy.validate(str(root / raw), must_exist=True)
                normalized = str(candidate.relative_to(root)).replace("\\", "/")
                if normalized not in parsed:
                    parsed.append(normalized)

            if sorted(parsed) != sorted(set(expected)):
                return ActionResult(False, "patch targets do not match authorized targets", backend=self.name)

            patch_bytes = patch_content.encode("utf-8")
            check = subprocess.run(
                ["git", "apply", "--check", "-"],
                cwd=str(root),
                input=patch_bytes,
                capture_output=True,
                timeout=30,
            )
            if check.returncode != 0:
                return ActionResult(False, "patch dry-run failed: " + check.stderr.decode("utf-8", errors="replace").strip()[:200], backend=self.name)

            applied = subprocess.run(
                ["git", "apply", "-"],
                cwd=str(root),
                input=patch_bytes,
                capture_output=True,
                timeout=60,
            )
            if applied.returncode != 0:
                return ActionResult(False, "patch apply failed: " + applied.stderr.decode("utf-8", errors="replace").strip()[:200], backend=self.name)

            return ActionResult(
                True,
                "Filesystem action completed",
                data={"repo_root": str(root), "target_paths": parsed},
                backend=self.name,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            return ActionResult(False, str(exc), backend=self.name)

    def restore_file_bytes_guarded(
        self,
        target: str | Path,
        restore_content: bytes,
        expected_current_sha256: str,
    ) -> ActionResult:
        """Restore one existing file from sealed bytes, fail-closed on drift.

        This is a bounded recovery primitive, not a generic write capability.
        The caller must supply the digest of the currently authorized post-state.
        """
        import hashlib

        try:
            path = self.policy.validate(str(target), must_exist=True)
            if not path.is_file():
                return ActionResult(False, "rollback target is not a file", backend=self.name)
            if not isinstance(restore_content, (bytes, bytearray)):
                return ActionResult(False, "restore content must be bytes", backend=self.name)
            if (
                not isinstance(expected_current_sha256, str)
                or len(expected_current_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in expected_current_sha256.lower())
            ):
                return ActionResult(False, "expected current sha256 is invalid", backend=self.name)

            current = path.read_bytes()
            observed = hashlib.sha256(current).hexdigest()
            if observed != expected_current_sha256.lower():
                return ActionResult(
                    False,
                    "rollback target drifted",
                    data={"observed_sha256": observed},
                    backend=self.name,
                )

            restored = bytes(restore_content)
            restored_sha = hashlib.sha256(restored).hexdigest()
            tmp = path.parent / f".{path.name}.{os.getpid()}.jarjar.rollback.tmp"
            tmp.write_bytes(restored)

            # Recheck the live target immediately before replacement.
            observed_recheck = hashlib.sha256(path.read_bytes()).hexdigest()
            if observed_recheck != expected_current_sha256.lower():
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
                return ActionResult(
                    False,
                    "rollback target drifted before replace",
                    data={"observed_sha256": observed_recheck},
                    backend=self.name,
                )

            os.replace(tmp, path)
            realized = hashlib.sha256(path.read_bytes()).hexdigest()
            if realized != restored_sha:
                return ActionResult(
                    False,
                    "rollback realized state mismatch",
                    data={"observed_sha256": realized, "expected_sha256": restored_sha},
                    backend=self.name,
                )
            return ActionResult(
                True,
                "Filesystem rollback completed",
                data={
                    "path": str(path),
                    "restored_sha256": restored_sha,
                    "previous_sha256": expected_current_sha256.lower(),
                    "bytes": len(restored),
                },
                backend=self.name,
            )
        except (OSError, ValueError) as exc:
            return ActionResult(False, str(exc), backend=self.name)

    def execute(self, request: ActionRequest) -> ActionResult:
        try:
            if request.capability == "file.open":
                path = self.policy.validate(self._arg(request, "path"), must_exist=True)
                os.startfile(str(path))
                data = {"path": str(path)}
            elif request.capability == "file.reveal":
                path = self.policy.validate(self._arg(request, "path"), must_exist=True)
                import subprocess
                subprocess.Popen(["explorer.exe", "/select,", str(path)])
                data = {"path": str(path)}
            elif request.capability == "folder.create":
                path = self.policy.validate(self._arg(request, "path"))
                path.mkdir(parents=True, exist_ok=False)
                data = {"path": str(path)}
            elif request.capability == "file.copy":
                source = self.policy.validate(self._arg(request, "source"), must_exist=True)
                target = self.policy.validate(self._arg(request, "target"))
                if source.is_dir():
                    shutil.copytree(source, target)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                data = {"source": str(source), "target": str(target)}
            elif request.capability == "file.move":
                source = self.policy.validate(self._arg(request, "source"), must_exist=True)
                target = self.policy.validate(self._arg(request, "target"))
                target.parent.mkdir(parents=True, exist_ok=True)
                result = shutil.move(str(source), str(target))
                data = {"source": str(source), "target": str(Path(result).resolve(strict=False))}
            elif request.capability == "file.delete":
                path = self.policy.validate(self._arg(request, "path"), must_exist=True)
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                data = {"path": str(path)}
            else:
                return ActionResult(False, "unsupported filesystem capability", backend=self.name)
        except (OSError, ValueError) as exc:
            return ActionResult(False, str(exc), backend=self.name)
        return ActionResult(True, "Filesystem action completed", data=data, backend=self.name)

    @staticmethod
    def _arg(request: ActionRequest, key: str) -> str:
        value = request.arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing filesystem argument: {key}")
        return value.strip()
