# G3 Browser V0 Freeze

Status: `BROWSER_V0_STATUS=CLOSED_WITH_DEFERRED_LIMITS`

This document freezes the governed Browser V0 public authority surface. It is a
documentation and governance artifact only. It does not add a capability, widen
authority, or start G3-E2 work.

Reference heads for this freeze request:

- JarJar: `67fb5e6`
- Obsidia: `7159187b`

## Public Governed Capabilities

The Browser V0 public governed surface is limited to:

- `BROWSER_READ`
- `BROWSER_NAVIGATE`
- `BROWSER_ACTIVATE_LINK`
- `BROWSER_SET_DISCLOSURE`
- `BROWSER_SET_CHECKED`
- `BROWSER_SELECT_RADIO`
- `BROWSER_SELECT_OPTION`
- `BROWSER_SET_FIELD_VALUE`
- `BROWSER_SUBMIT_FORM_NAVIGATION_V0`

The Browser V0 public governed surface does not include:

- generic click
- generic fill
- generic select
- generic submit
- generic JavaScript or evaluate execution

## Authority

- `KX108_ONLY=YES`
- `OPENJARVIS_AUTHORITY=NONE`
- `JARJAR_AUTHORITY=NONE`

JarJar is the physical browser executor layer. Obsidia/KX108 remains the
governed authority layer. JarJar execution success, Playwright success, or lack
of an exception is not authority.

## Proof Contract

Browser V0 proof is:

`POST_OBSERVATION_NOT_EXCEPTION`

The closure proof requires observed physical pre-state, a bound descriptor,
EAH/human/KX108 governance, TOCTOU checks before execution, and independent
post-observation where the capability contract requires realized state.

## Submit Uncertainty States

Browser submit V0 recognizes these states:

- `NOT_DISPATCHED`
- `DISPATCHED`
- `RESPONSE_OBSERVED`
- `POSTCONDITION_CONFIRMED`
- `DISPATCHED_OUTCOME_UNCERTAIN`

`POSTCONDITION_CONFIRMED` is the only successful V0 submit closure state.
`DISPATCHED_OUTCOME_UNCERTAIN` is not silently promoted to success.

## Replay Boundary

- No automatic physical resubmission.
- No idempotency assumption.
- Submit replay is evidence-only.

Any future replay-capable browser work must define a new contract before it can
reopen physical dispatch.

## Privacy Boundary

Browser V0 freezes these field-value privacy constraints:

- No field plaintext in PSA.
- No field plaintext in EAH.
- No field plaintext in descriptor.
- No field plaintext in receipt.
- No field plaintext in runtime result.

GET submit proof uses hashed and canonical endpoint evidence. It must not persist
full query plaintext as proof material.

## Non-Blocking Audit Notes

`PLAYWRIGHT_ENVIRONMENT_LIMIT=BrowserType.launch spawn EPERM`

This is a Windows/local environment limitation for real Playwright launch in the
audited environment. It is not a Browser V0 governance blocker.

`GRAPH_READ_PREPARE_CONFLICT=actual PC_GOVERNED_READ vs legacy test expecting write-family`

The read-family graph conflict is a legacy expectation mismatch. Browser read is
read authority, not write authority, and this mismatch is not a Browser V0
closure blocker.

## Deferred Limits Registry

| ID | Boundary | Why Deferred | Why It Does Not Block V0 | Required Future Contract |
| --- | --- | --- | --- | --- |
| `BROWSER_DEFER_01` generic click | No public generic click surface. | Generic click lacks semantic intent and postcondition. | V0 exposes semantic actions only. | Define intent class, target identity, side-effect model, and postcondition proof. |
| `BROWSER_DEFER_02` generic fill | No public generic fill surface. | Generic fill would bypass field privacy and type policy. | V0 exposes `BROWSER_SET_FIELD_VALUE` with bounded field classes. | Define privacy-safe descriptor, supported types, sensitive-field policy, and post proof. |
| `BROWSER_DEFER_03` generic submit | No public generic submit surface. | Generic submit would hide method, endpoint, and dispatch uncertainty. | V0 exposes GET form submit only. | Define method policy, dispatch states, endpoint rules, replay policy, and proof taxonomy. |
| `BROWSER_DEFER_04` POST forms | POST form submission is unsupported in V0. | POST has higher side-effect and body privacy risk. | GET V0 is closed separately. | Define body privacy, idempotency, dispatch, replay, and confirmation rules. |
| `BROWSER_DEFER_05` XHR/fetch semantic success | XHR/fetch application success is not claimed. | Browser transport does not prove application semantics. | V0 proves bounded navigation/transport only. | Define request classification, response semantics, and application-level proof. |
| `BROWSER_DEFER_06` login/password | Password/login workflows are rejected or deferred. | Secret handling and account authority need separate governance. | V0 blocks sensitive password classes. | Define credential custody, approval scope, secret handling, and audit receipts. |
| `BROWSER_DEFER_07` OTP/payment/card | OTP, payment, and card workflows are rejected or deferred. | These are high-risk financial/authentication actions. | V0 excludes them from field and submit contracts. | Define explicit high-risk authorization, secret handling, compliance, and rollback boundaries. |
| `BROWSER_DEFER_08` destructive actions | Destructive browser actions are not a V0 class. | Destruction needs object authority and recovery semantics. | V0 capabilities are bounded by named semantic contracts. | Define destructive-action taxonomy, confirmation, evidence, and undo/irreversibility policy. |
| `BROWSER_DEFER_09` message send | Sending messages is not a V0 class. | Message send has social/account authority distinct from form navigation. | V0 does not claim communication authority. | Define recipient identity, content binding, send confirmation, and audit receipt. |
| `BROWSER_DEFER_10` cross-origin submit | Cross-origin submit is rejected or deferred. | Cross-origin navigation changes risk and proof boundary. | V0 GET submit is same-origin. | Define approved origin transition, redirect policy, and post-state proof. |
| `BROWSER_DEFER_11` multi-select | Multi-select is unsupported in V0. | Multiple option state requires a separate state model. | V0 select option is single-select only. | Define selection set identity, add/remove semantics, and complete post proof. |
| `BROWSER_DEFER_12` contenteditable | Contenteditable mutation is unsupported in V0. | Text editing surface differs from form field semantics. | V0 field writes are bounded to supported input and textarea types. | Define editor identity, plaintext privacy, selection/caret handling, and post proof. |
| `BROWSER_DEFER_13` number/date/time/datetime-local | These field types are deferred. | Browser normalization and locale constraints need separate proof. | V0 supports only bounded text-like fields. | Define canonical value rules, validation, locale handling, and post proof. |
| `BROWSER_DEFER_14` iframe/frame identity | Iframe and frame identity are deferred. | Frame targeting changes authority and state anchors. | V0 targets the current bounded page context. | Define frame identity, origin policy, selector scope, and post-state anchoring. |
| `BROWSER_DEFER_15` radio peer deselection proof | Peer deselection proof is deferred. | V0 proves selected target, not complete peer-group transition. | Positive radio selection is still bounded and verified. | Define group inventory, peer-state proof, and form-owner consistency. |
| `BROWSER_DEFER_16` same-page autosave/XHR completeness | Same-page autosave/XHR completeness is not claimed. | Browser-visible DOM state may not capture background application writes. | V0 does not claim complete application side-effect coverage. | Define network observation, application confirmation, and uncertainty states. |
| `BROWSER_DEFER_17` application-level submit success | Application success is not claimed. | Transport/navigation success does not imply business success. | V0 separates transport/navigation from application proof. | Define application success oracle, evidence, and failure classification. |
| `BROWSER_DEFER_18` full HTML successful-controls equivalence | Full HTML form-control equivalence is not claimed. | Complete browser form serialization has many edge cases. | V0 uses a bounded hash manifest contract. | Define successful-controls parity rules and conformance evidence. |
| `BROWSER_DEFER_19` complete redirect-chain proof | Complete redirect-chain proof is not claimed. | Redirect observability can be partial. | V0 relies on bounded same-origin/final postcondition proof. | Define redirect-chain capture, origin transitions, and mismatch handling. |
| `BROWSER_DEFER_20` real Playwright Windows EPERM environment limitation | Real Playwright launch hit `BrowserType.launch spawn EPERM`. | Environment blocked launch, not governed logic. | Browser V0 closure rests on bounded tests and governance audit; this is not a semantic blocker. | Resolve local execution permissions and rerun real Playwright integration. |
| `BROWSER_DEFER_21` graph READ-family legacy expectation mismatch | Browser read is `PC_GOVERNED_READ`; a legacy test expected write-family. | The test expectation is broader than the read capability semantics. | Read authority being read-family is correct for V0 closure. | Update graph tests/contracts to distinguish read-family from write-family browser caps. |

## Freeze Rule

Future work must not broaden the public browser authority surface by reusing
Browser V0 names. Any POST, XHR, login, payment, destructive, message-send,
iframe, contenteditable, replay, generic click/fill/select/submit, or JavaScript
execution work must open a new governed contract with explicit authority,
privacy, replay, dispatch, and proof semantics.
