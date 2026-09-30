# UFO² DONOR AUDIT — WINDOWS STRUCTURED LAYER

Status: PARTIAL ADOPTION / JARVIS-OWNED CONTRACTS

Upstream donor: Microsoft UFO² / repository `microsoft/UFO`.
Observed upstream revision during audit: `a795552d976c4c019d7c2f778a0effb5cef7de6b`.
License: MIT.

## Scope

Only UFO² Windows automation ideas/primitives are in scope here.

Jarvis does NOT adopt UFO² agent ownership, LLM routing, prompt system,
conversation state, task authority, or ActionExecutor as canonical authority.

## Mapping

| UFO² area | Decision | Jarvis treatment |
| --- | --- | --- |
| `ui_control/inspector.py` | ADAPT | live UI inspection behind Jarvis driver |
| `ui_control/controller.py` | ADAPT | named-control actions behind Jarvis capabilities |
| `ui_control/control_filter.py` | REUSE CONCEPT | filtering/validation to be added incrementally |
| `ui_control/ui_tree.py` | REUSE CONCEPT | serializable UI tree, no donor wrapper leakage |
| `app_apis/*` WinCOM receivers | HOLD / AUDIT NEXT | potentially useful for Office/native APIs |
| `action_execution.py` | REJECT AS AUTHORITY | Jarvis ActionRouter remains canonical |
| `puppeteer.py` queue/receiver ownership | REJECT AS CANONICAL | useful patterns only |
| UFO agents / prompts / LLM | REJECT FOR THIS LAYER | no runtime dependency |

## Adopted seam

Jarvis now owns a `StructuredUIBackend` with capabilities:

- `control.list`
- `control.click`
- `control.set_text`
- `control.read_text`

The existing `UIADriver` now exposes a bounded live descendant-control
snapshot (max 200 controls) as plain serializable dictionaries. No pywinauto
wrapper crosses into Jarvis core.

## Invariants

- ActionRouter remains the only action routing authority.
- PermissionPolicy still runs before this backend.
- Structured UI remains above visual fallback by backend priority.
- No raw visual coordinates are required for named-control actions.
- Donor objects/wrappers do not become canonical Jarvis state.
- A fresh UI inspection is required when the caller wants current control state.

## Next donor step

Audit UFO² `app_apis/*` WinCOM receivers, particularly Word, Excel and
PowerPoint, then decide whether to expose a narrow `windows.com` adapter.
After structured Windows closure, continue to UI-TARS for semantic visual
grounding only.
