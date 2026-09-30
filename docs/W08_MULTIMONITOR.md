# W08 — Multi-monitor virtual desktop

Status: STRUCTURAL IMPLEMENTED / PHYSICAL VALIDATION PENDING

Jarjar visual fallback now uses Windows virtual-desktop coordinates rather
than assuming the primary display begins at (0, 0).

Important properties:

- active monitors are enumerated through Win32 `EnumDisplayMonitors`;
- secondary monitors may use negative x/y origins;
- screenshots cover the fresh virtual-desktop bounding box;
- every observation records the monitor rectangles and coordinate space;
- clicks are accepted only when the point belongs to a real monitor;
- empty gaps inside the virtual bounding rectangle are rejected;
- historical Screenpipe observations remain invalid as live action handles.

This does not change backend priority: browser/structured Windows automation
remain preferred. Visual coordinate control is still a low-priority fallback.

Physical PASS requires enumeration/capture on the target Windows machine.
