import json
import sys
import os
from dataclasses import dataclass, field

# Windows 下强制 stdout 使用 UTF-8，避免中文乱码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.system("")  # 启用 VT100 / ANSI 转义序列

import asyncio
import requests


REQUEST_TIMEOUT_SECONDS = 30
RESPONSE_BODY_LIMIT = 4096


class ConfigError(ValueError):
    """Raised when config.json has an invalid shape or value."""


@dataclass
class HttpResult:
    url: str
    proxies: dict
    status_code: int | None = None
    reason: str = ""
    headers: dict = field(default_factory=dict)
    body: str = ""
    error: str | None = None


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_proxy_url(raw, field_name="proxy.playwright.server"):
    """
    从代理 URL 中拆出 (server, username, password)。
    支持 socks5://user:pass@host:port 或 http://host:port 等格式。
    """
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(
            f"{field_name} must include a URL scheme and hostname, "
            "for example socks5://127.0.0.1:1080"
        )

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{field_name} has an invalid port") from exc

    username = parsed.username or ""
    password = parsed.password or ""
    # 剔除 userinfo 后的纯 server 地址
    hostname = parsed.hostname
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    server = urlunparse(parsed._replace(netloc=hostname + (f":{port}" if port else "")))
    return server, username, password


def _is_positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_config(cfg):
    if not isinstance(cfg, dict):
        raise ConfigError("config must be a JSON object")

    url = cfg.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ConfigError("url must be a non-empty string")

    proxy_cfg = cfg.get("proxy", {})
    if proxy_cfg is None:
        proxy_cfg = {}
    if not isinstance(proxy_cfg, dict):
        raise ConfigError("proxy must be an object")

    for name in ("requests", "playwright"):
        section = proxy_cfg.get(name, {})
        if section is None:
            section = {}
        if not isinstance(section, dict):
            raise ConfigError(f"proxy.{name} must be an object")

        enabled = section.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ConfigError(f"proxy.{name}.enabled must be a boolean")

        server = section.get("server", "")
        if enabled:
            if not isinstance(server, str) or not server.strip():
                raise ConfigError(f"proxy.{name}.server must be a non-empty string when enabled")
            try:
                _parse_proxy_url(server, f"proxy.{name}.server")
            except ValueError as exc:
                raise ConfigError(str(exc)) from exc

    browser_cfg = cfg.get("browser", {})
    if browser_cfg is None:
        browser_cfg = {}
    if not isinstance(browser_cfg, dict):
        raise ConfigError("browser must be an object")

    channel = browser_cfg.get("channel", "chromium")
    if not isinstance(channel, str) or not channel.strip():
        raise ConfigError("browser.channel must be a non-empty string")

    executable_path = browser_cfg.get("executable_path", "")
    if not isinstance(executable_path, str):
        raise ConfigError("browser.executable_path must be a string")

    for field_name in ("headless", "devtools"):
        value = browser_cfg.get(field_name, False if field_name == "headless" else True)
        if not isinstance(value, bool):
            raise ConfigError(f"browser.{field_name} must be a boolean")

    viewport = browser_cfg.get("viewport", {"width": 1280, "height": 720})
    if not isinstance(viewport, dict):
        raise ConfigError("browser.viewport must be an object")
    for dimension in ("width", "height"):
        value = viewport.get(dimension)
        if not _is_positive_int(value):
            raise ConfigError(f"browser.viewport.{dimension} must be a positive integer")


def build_proxies(cfg):
    """
    从 cfg["proxy"]["requests"] 构造 requests 库的 proxies 字典。
    server 可以是 http:// https:// socks5:// 等任意协议。
    socks5 需要 pip install 'requests[socks]'。
    """
    p = cfg.get("proxy", {}).get("requests", {})
    if not p.get("enabled"):
        return {}
    server = p.get("server")
    if not server:
        return {}
    return {"http": server, "https": server}


def build_playwright_proxy(cfg):
    """
    从 cfg["proxy"]["playwright"] 构造 Playwright 的 proxy 字典。
    server 可以是 http:// https:// socks5:// 等任意协议。
    认证信息从 URL 中解析，拆为 server / username / password 独立字段。
    """
    p = cfg.get("proxy", {}).get("playwright", {})
    if not p.get("enabled"):
        return None
    raw = p.get("server")
    if not raw:
        return None
    server, username, password = _parse_proxy_url(raw, "proxy.playwright.server")
    result = {"server": server}
    if username:
        result["username"] = username
        result["password"] = password
    return result


def fetch_http(url, proxies, session=None, timeout=REQUEST_TIMEOUT_SECONDS):
    owns_session = session is None
    if session is None:
        session = requests.Session()

    try:
        resp = session.get(url, proxies=proxies, timeout=timeout)
    except requests.RequestException as e:
        return HttpResult(url=url, proxies=dict(proxies), error=str(e))
    finally:
        if owns_session:
            session.close()

    return HttpResult(
        url=url,
        proxies=dict(proxies),
        status_code=resp.status_code,
        reason=resp.reason,
        headers=dict(resp.headers),
        body=resp.text,
    )


def _truncate(text, limit=RESPONSE_BODY_LIMIT):
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... [truncated]"


def print_http_result(result):
    """
    打印 requests 请求结果。
    """
    print("=" * 60)
    print("HTTP Request via requests")
    print("=" * 60)
    print(f"URL : {result.url}")
    print(f"Proxy: {result.proxies if result.proxies else 'None (direct)'}")
    print()

    if result.error:
        print(f"请求失败: {result.error}")
        return

    print(f"Status: {result.status_code} {result.reason}")
    print()
    print("--- Response Headers ---")
    for k, v in result.headers.items():
        print(f"  {k}: {v}")

    print()
    print(f"--- Response Body (truncated to {RESPONSE_BODY_LIMIT} chars) ---")
    print(_truncate(result.body))


def http_request(url, proxies):
    """
    使用 requests 发起 GET 请求，打印响应头和响应体。
    """
    result = fetch_http(url, proxies)
    print_http_result(result)
    return result


async def playwright_browser(
    url,
    cfg,
    browser_cfg,
    playwright_context_factory=None,
    wait_for_input=input,
):
    """
    使用 Playwright 打开浏览器，可选开启开发者工具，访问指定 URL。
    """
    print()
    print("=" * 60)
    print("Playwright Browser")
    print("=" * 60)

    channel = browser_cfg.get("channel", "chromium")
    executable_path = browser_cfg.get("executable_path", "")
    headless = browser_cfg.get("headless", False)
    devtools = browser_cfg.get("devtools", True)
    viewport = browser_cfg.get("viewport", {"width": 1280, "height": 720})

    proxy = build_playwright_proxy(cfg)

    print(f"Browser  : {executable_path if executable_path else channel}")
    print(f"Headless : {headless}")
    print(f"DevTools : {devtools}")
    print(f"URL      : {url}")
    print(f"Proxy    : {proxy['server'] if proxy else 'None (direct)'}")
    print()

    if playwright_context_factory is None:
        from playwright.async_api import async_playwright

        playwright_context_factory = async_playwright

    browser = None
    context = None

    async with playwright_context_factory() as pw:
        bundled = {
            "chromium": pw.chromium,
            "firefox": pw.firefox,
            "webkit": pw.webkit,
        }
        system_channels = {
            "chrome", "chrome-beta", "chrome-dev", "chrome-canary",
            "msedge", "msedge-beta", "msedge-dev", "msedge-canary",
        }

        if channel in bundled:
            browser_type = bundled[channel]
        elif channel in system_channels:
            browser_type = pw.chromium
        else:
            print(f"未知 channel '{channel}'，fallback 到 chromium")
            browser_type = pw.chromium

        launch_args = []
        if devtools and (channel in system_channels or channel == "chromium"):
            launch_args.append("--auto-open-devtools-for-tabs")

        try:
            browser = await browser_type.launch(
                headless=headless,
                executable_path=executable_path or None,
                channel=channel if (not executable_path and channel in system_channels) else None,
                args=launch_args,
            )

            context_kwargs = {"viewport": viewport}
            if proxy:
                context_kwargs["proxy"] = proxy

            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()

            # DevTools 需要时间初始化，先空白页让面板就绪，再导航
            if devtools and channel in system_channels | {"chromium"}:
                await asyncio.sleep(1.5)

            print("正在打开页面，请查看浏览器窗口...")
            await page.goto(url, wait_until="load", timeout=60000)

            print(f"当前页面标题: {await page.title()}")
            print(f"当前 URL     : {page.url}")
            print()
            print("按 Enter 键关闭浏览器并退出...")
            await asyncio.to_thread(wait_for_input)
        finally:
            if context is not None:
                await context.close()
            if browser is not None:
                await browser.close()


async def main():
    cfg = load_config()
    validate_config(cfg)
    url = cfg["url"]
    browser_cfg = cfg.get("browser", {})

    # ====== 任务 1: HTTP 请求（requests） ======
    proxies = build_proxies(cfg)
    http_request(url, proxies)

    # ====== 任务 2: Playwright 浏览器（async，不依赖 greenlet） ======
    await playwright_browser(url, cfg, browser_cfg)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ConfigError as exc:
        print(f"配置错误: {exc}", file=sys.stderr)
        raise SystemExit(2)
