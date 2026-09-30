from jarvis.integrations.win32_driver import Win32Driver


def test_powershell_json_wrapper_uses_script_block(monkeypatch):
    calls = {}

    class Result:
        returncode = 0
        stdout = '{"ok":true}'
        stderr = ""

    def fake_run(args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = Win32Driver()._run_powershell_json("$x = 1\n$x")

    assert result == {"ok": True}
    command = calls["args"][-1]
    assert command.startswith("& {\n")
    assert "\n} | ConvertTo-Json -Compress -Depth 4" in command
