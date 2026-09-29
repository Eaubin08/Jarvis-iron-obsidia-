import pytest

pytest.importorskip("playwright.sync_api")

from jarvis.integrations.playwright_driver import PlaywrightDriver


HTML = """<!doctype html>
<html>
  <head><title>Jarvis Browser Fixture</title></head>
  <body>
    <input id="query" />
    <button id="save" onclick="document.querySelector('#result').textContent='saved'">Save</button>
    <div id="result">idle</div>
  </body>
</html>"""


def test_real_chromium_navigate_read_fill_click(tmp_path):
    page_file = tmp_path / "fixture.html"
    page_file.write_text(HTML, encoding="utf-8")
    driver = PlaywrightDriver(headless=True)
    try:
        nav = driver.navigate(page_file.as_uri())
        assert nav["title"] == "Jarvis Browser Fixture"

        driver.fill("#query", "hello jarvis")
        assert driver.read("#query")["text"] == ""

        driver.click("#save")
        assert driver.read("#result")["text"] == "saved"
    finally:
        driver.close()
