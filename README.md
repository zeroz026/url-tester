# URL Tester

HTTP 请求 + Playwright 浏览器双模式 URL 测试工具，支持 HTTP/HTTPS/SOCKS5 代理。

## 初始化

```bash
cd url-tester

# 1. 创建 venv
python -m venv venv

# 2. 激活 venv
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装 Playwright 浏览器（chromium/firefox/webkit）
playwright install chromium
```

## 配置

编辑 `config.json`：

| 字段 | 说明 |
|------|------|
| `url` | 目标 URL |
| `proxy.requests.enabled` | 是否为 `requests` 请求启用代理 (true/false) |
| `proxy.requests.server` | `requests` 代理地址，例如 `http://127.0.0.1:8080` 或 `socks5://127.0.0.1:1080` |
| `proxy.playwright.enabled` | 是否为 Playwright 浏览器启用代理 (true/false) |
| `proxy.playwright.server` | Playwright 代理地址，必须包含协议和主机，例如 `socks5://127.0.0.1:1080` |
| `browser.channel` | 浏览器: `chromium` / `chrome` / `chrome-beta` / `msedge` / `firefox` / `webkit` 等 |
| `browser.executable_path` | 浏览器可执行文件全路径，优先级高于 channel (为空则忽略) |
| `browser.headless` | 无头模式 (true/false) |
| `browser.devtools` | 打开开发者工具 (仅 chromium 内核) |
| `browser.stealth` | 启用反检测隐身模式，注入 JS evasion 脚本 + Chrome 反自动化标志 (true/false) |
| `browser.locale` | stealth 模式下模拟的地区语言，默认 `en-US`。中文环境填 `zh-CN` |
| `browser.timezone_id` | stealth 模式下模拟的时区，默认 `America/New_York`。中文环境填 `Asia/Shanghai` |
| `browser.viewport` | 窗口大小 `{"width": 1280, "height": 720}` |

### 中文环境配置示例

```json
{
    "url": "https://httpbin.org/ip",
    "proxy": { ... },
    "browser": {
        "channel": "chromium",
        "headless": false,
        "devtools": true,
        "stealth": true,
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "viewport": { "width": 1280, "height": 720 }
    }
}
```

## 执行

配置 `run.sh` / `run.bat` 中的 `PYTHON_PATH` 指向 venv 的 Python，然后：

```bash
# Linux/Mac
./run.sh

# Windows
run.bat
```

或直接运行：

```bash
python main.py
```

## 做了什么

脚本按顺序执行两个任务：

1. **HTTP 请求** — `requests` 库发起 GET，打印响应头和响应体
2. **Playwright 浏览器** — 打开浏览器，开启 DevTools，导航到目标 URL。按 Enter 关闭浏览器退出
