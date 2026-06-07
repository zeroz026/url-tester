import unittest
from unittest.mock import patch

import requests


from main import (
    ConfigError,
    build_playwright_proxy,
    build_proxies,
    fetch_http,
    playwright_browser,
    validate_config,
)


class ProxyConfigTests(unittest.TestCase):
    def test_build_proxies_uses_requests_proxy_server(self):
        cfg = {
            "proxy": {
                "requests": {
                    "enabled": True,
                    "server": "socks5://127.0.0.1:1080",
                }
            }
        }

        self.assertEqual(
            build_proxies(cfg),
            {
                "http": "socks5://127.0.0.1:1080",
                "https": "socks5://127.0.0.1:1080",
            },
        )

    def test_build_playwright_proxy_strips_url_credentials(self):
        cfg = {
            "proxy": {
                "playwright": {
                    "enabled": True,
                    "server": "socks5://user:pass@127.0.0.1:1080",
                }
            }
        }

        self.assertEqual(
            build_playwright_proxy(cfg),
            {
                "server": "socks5://127.0.0.1:1080",
                "username": "user",
                "password": "pass",
            },
        )

    def test_build_playwright_proxy_rejects_server_without_scheme(self):
        cfg = {
            "proxy": {
                "playwright": {
                    "enabled": True,
                    "server": "127.0.0.1:1080",
                }
            }
        }

        with self.assertRaisesRegex(
            ValueError,
            "proxy.playwright.server must include a URL scheme and hostname",
        ):
            build_playwright_proxy(cfg)

    def test_validate_config_rejects_missing_url(self):
        with self.assertRaisesRegex(ConfigError, "url must be a non-empty string"):
            validate_config({})

    def test_validate_config_rejects_invalid_viewport(self):
        cfg = {
            "url": "https://example.com",
            "browser": {"viewport": {"width": 1280, "height": "720"}},
        }

        with self.assertRaisesRegex(
            ConfigError,
            "browser.viewport.height must be a positive integer",
        ):
            validate_config(cfg)

    def test_fetch_http_uses_provided_session_and_returns_result(self):
        class FakeResponse:
            status_code = 200
            reason = "OK"
            headers = {"Content-Type": "text/plain"}
            text = "hello"

        class FakeSession:
            def __init__(self):
                self.calls = []

            def get(self, url, proxies, timeout):
                self.calls.append((url, proxies, timeout))
                return FakeResponse()

        session = FakeSession()
        proxies = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}

        result = fetch_http("https://example.com", proxies, session=session, timeout=5)

        self.assertEqual(
            session.calls,
            [("https://example.com", proxies, 5)],
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.reason, "OK")
        self.assertEqual(result.headers, {"Content-Type": "text/plain"})
        self.assertEqual(result.body, "hello")
        self.assertIsNone(result.error)

    def test_fetch_http_returns_error_result_for_request_exception(self):
        class FakeSession:
            def get(self, url, proxies, timeout):
                raise requests.RequestException("network down")

        result = fetch_http("https://example.com", {}, session=FakeSession())

        self.assertIsNone(result.status_code)
        self.assertEqual(result.error, "network down")

    def test_playwright_browser_closes_resources_when_navigation_fails(self):
        fake = FakePlaywright(goto_error=RuntimeError("navigation failed"))

        async def run():
            with self.assertRaisesRegex(RuntimeError, "navigation failed"):
                await playwright_browser(
                    "https://example.com",
                    {},
                    {"headless": True, "devtools": False},
                    playwright_context_factory=fake.factory,
                    wait_for_input=lambda: None,
                )

        import asyncio

        asyncio.run(run())

        self.assertTrue(fake.context.closed)
        self.assertTrue(fake.browser.closed)

    def test_playwright_browser_waits_for_input_in_worker_thread(self):
        fake = FakePlaywright()
        calls = []

        def wait_for_input():
            calls.append("input")

        async def fake_to_thread(func):
            calls.append("to_thread")
            return func()

        async def run():
            with patch("main.asyncio.to_thread", side_effect=fake_to_thread):
                await playwright_browser(
                    "https://example.com",
                    {},
                    {"headless": True, "devtools": False},
                    playwright_context_factory=fake.factory,
                    wait_for_input=wait_for_input,
                )

        import asyncio

        asyncio.run(run())

        self.assertEqual(calls, ["to_thread", "input"])


class FakePlaywright:
    def __init__(self, goto_error=None):
        self.page = FakePage(goto_error)
        self.context = FakeContext(self.page)
        self.browser = FakeBrowser(self.context)
        browser_type = FakeBrowserType(self.browser)
        self.instance = type(
            "FakePlaywrightInstance",
            (),
            {
                "chromium": browser_type,
                "firefox": browser_type,
                "webkit": browser_type,
            },
        )()

    def factory(self):
        return FakePlaywrightContextManager(self.instance)


class FakePlaywrightContextManager:
    def __init__(self, instance):
        self.instance = instance

    async def __aenter__(self):
        return self.instance

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeBrowserType:
    def __init__(self, browser):
        self.browser = browser

    async def launch(self, **kwargs):
        self.launch_kwargs = kwargs
        return self.browser


class FakeBrowser:
    def __init__(self, context):
        self.context = context
        self.closed = False

    async def new_context(self, **kwargs):
        self.context_kwargs = kwargs
        return self.context

    async def close(self):
        self.closed = True


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    async def new_page(self):
        return self.page

    async def close(self):
        self.closed = True


class FakePage:
    def __init__(self, goto_error=None):
        self.goto_error = goto_error
        self.url = "https://example.com"

    async def goto(self, url, wait_until, timeout):
        if self.goto_error:
            raise self.goto_error
        self.url = url

    async def title(self):
        return "Example"


if __name__ == "__main__":
    unittest.main()
