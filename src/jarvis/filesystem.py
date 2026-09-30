"""Jarjar-owned filesystem actions with bounded path policy.

The path-policy shape is adapted from OpenJarvis' Apache-2.0 file tools:
resolve paths, restrict roots when configured, and block sensitive filenames.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil

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
