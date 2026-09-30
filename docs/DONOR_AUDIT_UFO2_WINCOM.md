# UFO² DONOR AUDIT — OFFICE WINCOM

Status: ADOPTED NARROWLY / NO DONOR AUTHORITY

Upstream donor: Microsoft UFO² (`microsoft/UFO`), MIT licensed.

## What UFO² contributes

The audited Office receivers show useful native COM patterns:

- Word: active document selection, table insertion, text/paragraph/table selection,
  font changes and SaveAs/export.
- Excel: sheet/range selection, native range reads/writes, table insertion,
  column manipulation and SaveAs/export.
- PowerPoint: presentation selection, slide background mutation and SaveAs/export.

UFO² wraps these capabilities inside its Receiver/Command/Puppeteer system.
Jarvis does not adopt that ownership layer.

## Jarvis mapping

Jarvis now exposes a narrower `OfficeCOMBackend` behind ActionRouter:

- `office.word.insert_table`
- `office.word.save_as`
- `office.excel.get_range`
- `office.excel.set_range`
- `office.powerpoint.set_background`
- `office.powerpoint.save_as`

The concrete `Win32OfficeCOMDriver` uses pywin32 COM directly and returns only
plain serializable dictionaries.

## Decisions

| UFO² primitive | Decision |
| --- | --- |
| WinCOMReceiverBasic dispatch pattern | REIMPLEMENT narrowly |
| Word insert/save primitives | ADAPT |
| Excel range read/write primitives | ADAPT |
| PowerPoint background/save primitives | ADAPT |
| object-name fuzzy matching | HOLD; avoid ambiguous targeting for now |
| command registry / ReceiverManager | REJECT as canonical runtime |
| AppPuppeteer ownership | REJECT as canonical runtime |
| silent exception swallowing in save/close helpers | REJECT; Jarvis fails closed |

## Safety / architecture

- ActionRouter and PermissionPolicy remain upstream of COM execution.
- No UFO² agent or LLM enters this path.
- No donor COM object crosses the adapter boundary.
- Ambiguous document matching is intentionally not adopted.
- Mutating Office actions can later be classified with stricter RiskClass /
  approval policy without changing the COM driver.

## Next

After unit closure, a physical Office gate may be run only on disposable local
documents. Then continue to UI-TARS for semantic visual grounding.
