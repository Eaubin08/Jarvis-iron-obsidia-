"""Stable UI Automation identity and a bounded, identity-bound text setter (G2-0).

JarJar stays a physical executor: no approval, no policy, no authority here. This
module only lets a caller (later: Obsidia governance) observe controls with a stable
identity, re-find exactly that control, and set exact text on it through UIA
ValuePattern.SetValue, then prove the result by reading the same control back.

Identity:
  PRIMARY  window_hwnd, process_id, runtime_id
  DRIFT    native_handle (if nonzero), automation_id (if present), control_type,
           class_name, framework_id, parent_runtime_id
Never identity: visible name / title, index, bounds. No fuzzy fallback: a control
whose primary identity or any bound drift field differs is a failure, never a
"closest" match.

Public surface (nothing else): list_controls_uia, find_control_by_identity,
read_value_by_identity, set_text_by_identity. No keyboard, mouse, invoke, raw COM or
pywinauto object ever leaves this module; values are reported as SHA-256 digests.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Protocol

MAX_CONTROLS = 200
TEXT_CONTROL_TYPES = frozenset({"Edit", "Document"})  # the only set_text targets
TOGGLE_OFF = 0           # ToggleState.Off
TOGGLE_ON = 1            # ToggleState.On
TOGGLE_INDETERMINATE = 2 # ToggleState.Indeterminate
CHECKBOX_CONTROL_TYPE = "CheckBox"


@dataclass(frozen=True)
class UIAControlIdentity:
    window_hwnd: int
    process_id: int
    runtime_id: tuple[int, ...]
    native_handle: int = 0
    automation_id: str = ""
    control_type: str = ""
    class_name: str = ""
    framework_id: str = ""
    parent_runtime_id: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.window_hwnd, int) or self.window_hwnd <= 0:
            raise ValueError("window_hwnd must be a positive int")
        if not isinstance(self.process_id, int) or self.process_id <= 0:
            raise ValueError("process_id must be a positive int")
        rid = tuple(int(x) for x in self.runtime_id)
        if not rid:
            raise ValueError("runtime_id is required")
        object.__setattr__(self, "runtime_id", rid)
        object.__setattr__(self, "parent_runtime_id", tuple(int(x) for x in self.parent_runtime_id))

    def to_dict(self) -> dict:
        data = asdict(self)
        data["runtime_id"] = list(self.runtime_id)
        data["parent_runtime_id"] = list(self.parent_runtime_id)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "UIAControlIdentity":
        if not isinstance(data, dict):
            raise ValueError("target identity must be a dict")
        allowed = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown identity fields: {sorted(unknown)}")
        return cls(
            window_hwnd=data.get("window_hwnd"),
            process_id=data.get("process_id"),
            runtime_id=tuple(data.get("runtime_id") or ()),
            native_handle=int(data.get("native_handle") or 0),
            automation_id=str(data.get("automation_id") or ""),
            control_type=str(data.get("control_type") or ""),
            class_name=str(data.get("class_name") or ""),
            framework_id=str(data.get("framework_id") or ""),
            parent_runtime_id=tuple(data.get("parent_runtime_id") or ()),
        )


class UIAElementSource(Protocol):
    """Internal access to live UIA elements. Implementations never leak their element
    objects outside StableUIAController."""

    def window_process_id(self, window_hwnd: int) -> int | None: ...
    def elements(self, window_hwnd: int) -> Iterable[Any]: ...
    def describe(self, element: Any) -> dict: ...
    def has_value_pattern(self, element: Any) -> bool: ...
    def is_read_only(self, element: Any) -> bool: ...
    def get_value(self, element: Any) -> str: ...
    def set_value(self, element: Any, text: str) -> None: ...
    def has_toggle_pattern(self, element: Any) -> bool: ...
    def get_toggle_state(self, element: Any) -> int: ...
    def do_toggle(self, element: Any) -> None: ...


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class IdentityError(Exception):
    """The live control is not exactly the bound identity (fail closed)."""


class StableUIAController:
    def __init__(self, source: UIAElementSource | None = None, *, max_controls: int = MAX_CONTROLS):
        self._source = source if source is not None else PywinautoUIASource()
        self._max = max_controls

    # ── read-only ──────────────────────────────────────────────────────────────
    def list_controls_uia(self, *, window_hwnd: int) -> dict:
        pid = self._window_pid(window_hwnd)
        controls = []
        for element in self._source.elements(window_hwnd):
            if len(controls) >= self._max:
                break
            info = self._source.describe(element)
            identity = self._identity_from(window_hwnd, pid, info)
            if identity is None:
                continue
            controls.append(self._sanitized(identity, info, element))
        return {"window_hwnd": window_hwnd, "process_id": pid, "controls": controls,
                "truncated": len(controls) >= self._max}

    def find_control_by_identity(self, target: UIAControlIdentity | dict) -> dict:
        identity = self._coerce(target)
        element, info = self._resolve(identity)
        return {"ok": True, **self._sanitized(identity, info, element)}

    def read_value_by_identity(self, target: UIAControlIdentity | dict) -> dict:
        identity = self._coerce(target)
        element, info = self._resolve(identity)
        if info.get("is_password"):
            raise IdentityError("password control: value is never read")
        if not self._source.has_value_pattern(element):
            raise IdentityError("control has no ValuePattern")
        value = self._source.get_value(element)
        return {"ok": True, "target_identity": identity.to_dict(),
                "value_sha256": _sha256(value), "value_length": len(value)}

    # ── bounded mutation ───────────────────────────────────────────────────────
    def set_text_by_identity(self, target: UIAControlIdentity | dict, exact_text: str) -> dict:
        if not isinstance(exact_text, str):
            raise ValueError("exact_text must be a string")
        identity = self._coerce(target)
        element, info = self._resolve(identity)
        if str(info.get("control_type") or "") not in TEXT_CONTROL_TYPES:
            # e.g. a TitleBar also exposes a writable ValuePattern: never a text-entry target
            raise IdentityError("control type is not a text-entry control")
        if not info.get("enabled"):
            raise IdentityError("control is disabled")
        if info.get("is_password"):
            raise IdentityError("password control: text entry is not supported")
        if not self._source.has_value_pattern(element):
            raise IdentityError("control has no ValuePattern")
        if self._source.is_read_only(element):
            raise IdentityError("control is read-only")

        self._source.set_value(element, exact_text)

        # realized state: re-find the SAME exact control and read its value back
        after, _ = self._resolve(identity)
        readback = self._source.get_value(after)
        requested_hash, readback_hash = _sha256(exact_text), _sha256(readback)
        if readback != exact_text:
            raise IdentityError("readback mismatch: control value differs from the requested text")
        return {"ok": True, "target_identity": identity.to_dict(),
                "requested_text_sha256": requested_hash, "readback_text_sha256": readback_hash,
                "value_match": True, "proof": "uia_value_pattern_readback"}

    def read_checked_by_identity(self, target: "UIAControlIdentity | dict") -> dict:
        identity = self._coerce(target)
        element, info = self._resolve(identity)
        if str(info.get("control_type") or "") != CHECKBOX_CONTROL_TYPE:
            raise IdentityError("control type is not CheckBox")
        if not self._source.has_toggle_pattern(element):
            raise IdentityError("control has no TogglePattern")
        state = self._source.get_toggle_state(element)
        return {"ok": True, "target_identity": identity.to_dict(),
                "toggle_state": state, "checked": state == TOGGLE_ON,
                "indeterminate": state == TOGGLE_INDETERMINATE}

    def set_checked_by_identity(self, target: "UIAControlIdentity | dict", target_checked: bool) -> dict:
        if not isinstance(target_checked, bool):
            raise ValueError("target_checked must be a bool")
        identity = self._coerce(target)
        element, info = self._resolve(identity)
        if str(info.get("control_type") or "") != CHECKBOX_CONTROL_TYPE:
            raise IdentityError("control type is not CheckBox")
        if not bool(info.get("enabled")):
            raise IdentityError("control is disabled")
        if not self._source.has_toggle_pattern(element):
            raise IdentityError("control has no TogglePattern")
        pre_state = self._source.get_toggle_state(element)
        if pre_state == TOGGLE_INDETERMINATE:
            raise IdentityError("checkbox is indeterminate: cannot set to exact state")
        target_state = TOGGLE_ON if target_checked else TOGGLE_OFF
        mutation_performed = False
        if pre_state != target_state:
            self._source.do_toggle(element)  # exactly one semantic transition, never repeated
            mutation_performed = True
        # verified no-op too: the realized state is always an independent post read of the
        # SAME re-acquired identity, never the pre-read value
        after, _ = self._resolve(identity)
        post_state = self._source.get_toggle_state(after)
        if post_state != target_state:
            raise IdentityError(
                f"realized state mismatch: expected {target_state}, got {post_state}")
        return {"ok": True, "target_identity": identity.to_dict(),
                "target_checked": target_checked,
                "pre_toggle_state": pre_state, "post_toggle_state": post_state,
                "mutation_performed": mutation_performed,
                "realized_state_verified": True,
                "proof": "uia_toggle_pattern_readback"}

    # ── internals ──────────────────────────────────────────────────────────────
    @staticmethod
    def _coerce(target: UIAControlIdentity | dict) -> UIAControlIdentity:
        if isinstance(target, UIAControlIdentity):
            return target
        return UIAControlIdentity.from_dict(target)

    def _window_pid(self, window_hwnd: int) -> int:
        if not isinstance(window_hwnd, int) or window_hwnd <= 0:
            raise ValueError("window_hwnd must be a positive int")
        pid = self._source.window_process_id(window_hwnd)
        if not pid:
            raise IdentityError("window not found")
        return int(pid)

    @staticmethod
    def _identity_from(window_hwnd: int, pid: int, info: dict) -> UIAControlIdentity | None:
        rid = tuple(info.get("runtime_id") or ())
        if not rid:
            return None  # dead / unidentifiable element: never addressable
        return UIAControlIdentity(
            window_hwnd=window_hwnd, process_id=int(info.get("process_id") or pid), runtime_id=rid,
            native_handle=int(info.get("native_handle") or 0),
            automation_id=str(info.get("automation_id") or ""),
            control_type=str(info.get("control_type") or ""),
            class_name=str(info.get("class_name") or ""),
            framework_id=str(info.get("framework_id") or ""),
            parent_runtime_id=tuple(info.get("parent_runtime_id") or ()),
        )

    def _resolve(self, identity: UIAControlIdentity):
        pid = self._window_pid(identity.window_hwnd)
        if pid != identity.process_id:
            raise IdentityError("process drift: window belongs to another process")
        matches = []
        for element in self._source.elements(identity.window_hwnd):
            info = self._source.describe(element)
            if tuple(info.get("runtime_id") or ()) == identity.runtime_id:
                matches.append((element, info))
        if not matches:
            raise IdentityError("target control not found (destroyed, recreated or other window)")
        if len(matches) > 1:
            raise IdentityError("runtime_id is not unique in the window")
        element, info = matches[0]
        live = self._identity_from(identity.window_hwnd, pid, info)
        if live is None or live.process_id != identity.process_id:
            raise IdentityError("process drift on the target control")
        for name in ("native_handle", "automation_id"):
            bound = getattr(identity, name)
            if bound and getattr(live, name) != bound:
                raise IdentityError(f"{name} drift")
        for name in ("control_type", "class_name", "framework_id", "parent_runtime_id"):
            bound = getattr(identity, name)
            if bound and getattr(live, name) != bound:
                raise IdentityError(f"{name} drift")
        return element, info

    def _sanitized(self, identity: UIAControlIdentity, info: dict, element: Any) -> dict:
        has_value = self._source.has_value_pattern(element)
        _htfn = getattr(self._source, "has_toggle_pattern", None)
        has_toggle = _htfn(element) if _htfn is not None else False
        return {
            "identity": identity.to_dict(),
            "name": str(info.get("name") or "")[:200],
            "enabled": bool(info.get("enabled")),
            "visible": bool(info.get("visible")),
            "is_password": bool(info.get("is_password")),
            "is_read_only": bool(self._source.is_read_only(element)) if has_value else None,
            "bounds": dict(info.get("bounds") or {}),
            "patterns": (["value"] if has_value else []) + (["toggle"] if has_toggle else []),
        }


class PywinautoUIASource:
    """Live UIA access through pywinauto backend="uia" (declared windows extra)."""

    def _desktop(self):
        try:
            import sys
            from jarvis.integrations.uia_driver import _prepare_comtypes_cache
            _prepare_comtypes_cache()  # same generated-wrapper location as UIADriver
            sys.coinit_flags = 2
            from pywinauto import Desktop
        except ImportError as exc:
            raise RuntimeError("pywinauto is not installed; install the windows optional dependency") from exc
        return Desktop(backend="uia")

    def _window(self, window_hwnd: int):
        return self._desktop().window(handle=window_hwnd).wrapper_object()

    def window_process_id(self, window_hwnd: int) -> int | None:
        try:
            return int(self._window(window_hwnd).element_info.process_id or 0) or None
        except Exception:
            return None

    def elements(self, window_hwnd: int):
        return self._window(window_hwnd).descendants()

    def describe(self, element) -> dict:
        info = element.element_info
        rid = info.runtime_id
        parent = info.parent
        try:
            is_password = bool(info.element.CurrentIsPassword)
        except Exception:
            is_password = True  # unknown sensitivity is treated as sensitive (fail closed)
        rect = info.rectangle
        return {
            "runtime_id": tuple(rid) if rid else (),
            "native_handle": int(info.handle or 0),
            "automation_id": info.automation_id or "",
            "control_type": info.control_type or "",
            "class_name": info.class_name or "",
            "framework_id": info.framework_id or "",
            "process_id": int(info.process_id or 0),
            "parent_runtime_id": tuple(parent.runtime_id or ()) if parent is not None else (),
            "name": info.name or "",
            "enabled": bool(info.enabled),
            "visible": bool(info.visible),
            "is_password": is_password,
            "bounds": {"left": int(rect.left), "top": int(rect.top),
                       "right": int(rect.right), "bottom": int(rect.bottom)},
        }

    def has_value_pattern(self, element) -> bool:
        try:
            element.iface_value
            return True
        except Exception:
            return False

    def is_read_only(self, element) -> bool:
        try:
            return bool(element.iface_value.CurrentIsReadOnly)
        except Exception:
            return True  # unknown is treated as read-only (fail closed)

    def get_value(self, element) -> str:
        return str(element.iface_value.CurrentValue)

    def set_value(self, element, text: str) -> None:
        element.iface_value.SetValue(text)

    def has_toggle_pattern(self, element) -> bool:
        try:
            element.iface_toggle
            return True
        except Exception:
            return False

    def get_toggle_state(self, element) -> int:
        return int(element.iface_toggle.CurrentToggleState)

    def do_toggle(self, element) -> None:
        element.iface_toggle.Toggle()
