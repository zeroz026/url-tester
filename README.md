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
| `proxy.enabled` | 是否启用代理 (true/false) |
| `proxy.http` | HTTP 代理地址 |
| `proxy.https` | HTTPS 代理地址 |
| `proxy.socks5` | SOCKS5 代理地址，优先级最高 |
| `browser.channel` | 浏览器: `chromium` / `chrome` / `chrome-beta` / `msedge` / `firefox` / `webkit` 等 |
| `browser.executable_path` | 浏览器可执行文件全路径，优先级高于 channel (为空则忽略) |
| `browser.headless` | 无头模式 (true/false) |
| `browser.devtools` | 打开开发者工具 (仅 chromium 内核) |
| `browser.viewport` | 窗口大小 `{"width": 1280, "height": 720}` |

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
