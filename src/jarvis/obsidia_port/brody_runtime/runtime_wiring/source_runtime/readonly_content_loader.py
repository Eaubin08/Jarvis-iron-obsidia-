# runtime_wiring/source_runtime/readonly_content_loader.py
# Read a file from a zip or directory source — read-only, never extracts to disk.
# Enforces: no .py, no path traversal, max preview size, safe extensions only.
# KX108_ONLY. No ACT. No write.

from __future__ import annotations
import hashlib
import pathlib
import zipfile
from dataclasses import dataclass
from typing import Optional

from .source_pack_resolver import ResolvedSourcePack, MissingSourcePackError

# Extensions allowed for content reading
_ALLOWED_EXTENSIONS = frozenset({
    ".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".rst",
})

# Extensions that are forbidden regardless
_FORBIDDEN_EXTENSIONS = frozenset({
    ".py", ".pyc", ".pyo", ".sh", ".bat", ".exe", ".dll", ".so",
    ".pyd", ".pyw", ".ps1", ".cmd",
})

_MAX_PREVIEW_BYTES = 8_192   # 8 KB preview max per file
_MAX_FILE_BYTES = 512_000    # 512 KB hard limit — refuse larger files entirely


class ForbiddenFileError(ValueError):
    """Raised when a file is forbidden to be read (e.g. .py, path traversal)."""


class FileTooLargeError(ValueError):
    """Raised when a file exceeds the size limit."""


@dataclass
class LoadedContent:
    internal_path: str
    file_name: str
    extension: str
    content_preview: str      # truncated to _MAX_PREVIEW_BYTES
    content_hash: str         # sha256 of full content
    bytes_read: int
    truncated: bool
    source_zip: str
    source_type: str          # "zip" or "directory"
    readonly: bool = True
    extracted_to_disk: bool = False


def _validate_path(internal_path: str) -> None:
    """Raise ForbiddenFileError on unsafe paths or extensions."""
    # No path traversal
    if ".." in internal_path or internal_path.startswith("/"):
        raise ForbiddenFileError(f"Path traversal attempt: {internal_path!r}")

    ext = pathlib.Path(internal_path).suffix.lower()
    if ext in _FORBIDDEN_EXTENSIONS:
        raise ForbiddenFileError(
            f"Forbidden extension {ext!r} in {internal_path!r} — DO_NOT_IMPORT_RUNTIME"
        )
    if ext and ext not in _ALLOWED_EXTENSIONS:
        raise ForbiddenFileError(
            f"Extension {ext!r} not in allowed list for {internal_path!r}"
        )


def load_file_from_pack(
    resolved: ResolvedSourcePack,
    internal_path: str,
    max_preview_bytes: int = _MAX_PREVIEW_BYTES,
) -> LoadedContent:
    """
    Read a file from a resolved source pack (zip or directory).

    Never extracts to disk. Never executes. Returns LoadedContent.
    Raises ForbiddenFileError for .py and unsafe paths.
    Raises FileTooLargeError for oversized files.
    """
    _validate_path(internal_path)

    if resolved.source_type == "zip":
        return _load_from_zip(resolved, internal_path, max_preview_bytes)
    else:
        return _load_from_directory(resolved, internal_path, max_preview_bytes)


def _load_from_zip(
    resolved: ResolvedSourcePack, internal_path: str, max_preview_bytes: int
) -> LoadedContent:
    with zipfile.ZipFile(resolved.resolved_path, "r") as zf:
        try:
            info = zf.getinfo(internal_path)
        except KeyError:
            raise FileNotFoundError(
                f"File {internal_path!r} not found in {resolved.source_zip}"
            )

        if info.file_size > _MAX_FILE_BYTES:
            raise FileTooLargeError(
                f"File {internal_path!r} is {info.file_size:,} bytes > limit {_MAX_FILE_BYTES:,}"
            )

        raw_bytes = zf.read(internal_path)

    content = raw_bytes.decode("utf-8", errors="replace")
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    preview = content[:max_preview_bytes]
    truncated = len(content) > max_preview_bytes

    return LoadedContent(
        internal_path=internal_path,
        file_name=pathlib.Path(internal_path).name,
        extension=pathlib.Path(internal_path).suffix.lower(),
        content_preview=preview,
        content_hash=content_hash,
        bytes_read=len(raw_bytes),
        truncated=truncated,
        source_zip=resolved.source_zip,
        source_type="zip",
    )


def _load_from_directory(
    resolved: ResolvedSourcePack, internal_path: str, max_preview_bytes: int
) -> LoadedContent:
    target = resolved.resolved_path.joinpath(*internal_path.replace("\\", "/").split("/"))
    if not target.is_file():
        raise FileNotFoundError(
            f"File {internal_path!r} not found in directory {resolved.resolved_path}"
        )

    stat = target.stat()
    if stat.st_size > _MAX_FILE_BYTES:
        raise FileTooLargeError(
            f"File {internal_path!r} is {stat.st_size:,} bytes > limit {_MAX_FILE_BYTES:,}"
        )

    raw_bytes = target.read_bytes()
    content = raw_bytes.decode("utf-8", errors="replace")
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    preview = content[:max_preview_bytes]
    truncated = len(content) > max_preview_bytes

    return LoadedContent(
        internal_path=internal_path,
        file_name=target.name,
        extension=target.suffix.lower(),
        content_preview=preview,
        content_hash=content_hash,
        bytes_read=len(raw_bytes),
        truncated=truncated,
        source_zip=resolved.source_zip,
        source_type="directory",
    )
