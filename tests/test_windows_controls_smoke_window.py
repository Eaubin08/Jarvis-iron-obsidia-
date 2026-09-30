from scripts.smoke_windows_controls import _new_window_title


def test_new_window_title_prefers_notepad(monkeypatch):
    snapshots = iter([
        {10: "Existing", 20: "Other new", 30: "Sans titre - Bloc-notes"},
    ])
    monkeypatch.setattr(
        "scripts.smoke_windows_controls._visible_windows",
        lambda: next(snapshots),
    )
    assert _new_window_title({10}, timeout=0.1) == "Sans titre - Bloc-notes"
