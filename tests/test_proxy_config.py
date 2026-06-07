import sys
import types
import unittest


playwright = types.ModuleType("playwright")
async_api = types.ModuleType("playwright.async_api")
async_api.async_playwright = lambda: None
playwright.async_api = async_api
sys.modules.setdefault("playwright", playwright)
sys.modules.setdefault("playwright.async_api", async_api)

from main import build_playwright_proxy, build_proxies


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


if __name__ == "__main__":
    unittest.main()
