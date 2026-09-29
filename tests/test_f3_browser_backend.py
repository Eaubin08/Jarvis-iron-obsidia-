from jarvis.browser import BrowserBackend
from jarvis.contracts import ActionRequest, Capability


class FakeDriver:
    def __init__(self):
        self.calls = []

    def navigate(self, url):
        self.calls.append(("navigate", url))
        return {"url": url, "title": "Example"}

    def read(self, selector=None):
        self.calls.append(("read", selector))
        return {"text": "hello"}

    def click(self, selector):
        self.calls.append(("click", selector))
        return {"selector": selector}

    def fill(self, selector, value):
        self.calls.append(("fill", selector, value))
        return {"selector": selector}


def cap(name):
    return Capability(name, "browser")


def test_browser_backend_uses_structured_driver_not_coordinates():
    driver = FakeDriver()
    backend = BrowserBackend(driver)
    result = backend.execute(ActionRequest("browser.click", {"selector": "button#save"}))
    assert result.ok
    assert driver.calls == [("click", "button#save")]
    assert "x" not in result.data and "y" not in result.data


def test_navigation_requires_url():
    result = BrowserBackend(FakeDriver()).execute(ActionRequest("browser.navigate"))
    assert not result.ok
    assert "url" in result.message


def test_fill_requires_selector_and_value():
    backend = BrowserBackend(FakeDriver())
    assert not backend.execute(ActionRequest("browser.fill", {"selector": "#q"})).ok


def test_non_browser_family_is_not_claimed():
    backend = BrowserBackend(FakeDriver())
    assert not backend.can_execute(ActionRequest("browser.read"), Capability("browser.read", "visual"))
