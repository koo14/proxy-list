# ProxyScrape Proxy List & Gist Auto-Sync

[![Fetch Proxies](https://github.com/USER/REPO/actions/workflows/fetch-proxies.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/fetch-proxies.yml)
[![Upload Proxies to Gist](https://github.com/USER/REPO/actions/workflows/upload-to-gist.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/upload-to-gist.yml)

自动化从 [proxyscrape.com](https://proxyscrape.com) 抓取指定国家及协议（支持 **socks5, socks4, http, https**）的代理列表，进行标准格式化，并通过 GitHub Actions 自动覆写同步至指定的 GitHub Gist。

---

## 目录
- [项目特性](#项目特性)
- [文件与格式规范](#文件与格式规范)
- [目录结构](#目录结构)
- [快速开始与配置](#快速开始与配置)
  - [1. 配置 GitHub Secrets & Variables](#1-配置-github-secrets--variables)
  - [2. 自定义国家与协议列表](#2-自定义国家与协议列表)
- [工作流说明](#工作流说明)
  - [Action 1: 抓取与格式化代理列表 (fetch-proxies.yml)](#action-1-抓取与格式化代理列表-fetch-proxiesyml)
  - [Action 2: 同步覆写至 GitHub Gist (upload-to-gist.yml)](#action-2-同步覆写至-github-gist-upload-to-gistyml)
- [本地开发与测试](#本地开发与测试)
- [注意事项](#注意事项)

---

## 项目特性

1. **多协议选择支持**：支持 `socks5`、`socks4`、`http`、`https` 等多种协议，可在 Action 中自由组合选择（如 `"socks5"` 或 `"socks5,http,https"`）。
2. **多国家支持**：在 Action 配置文件或手动触发时轻松指定国家代码（如 `US,DE,GB,FR,JP,HK,SG` 或 `ALL`）。
3. **标准命名与格式**：
   - 文件名：`{COUNTRY_CODE}-{PROTOCOL}.txt`（如 `US-SOCKS5.txt`、`US-HTTP.txt`、`DE-SOCKS4.txt`）。
   - 内容格式：`{protocol}://xxx:yyy#{COUNTRY_CODE}-{PROTOCOL}-{Number}`。
4. **无预存代理噪点**：代码库默认不预置静态代理列表，仅由 GitHub Actions 定时或手动按需抓取生成。
5. **ProxyScrape Token 支持**：支持传入 ProxyScrape API Token/Key，未配置时自动回退到公开接口。
6. **两套独立 GitHub Actions**：
   - **Action 1 (Fetch)**：定时或手动抓取并提交到仓库 `proxies/` 目录。
   - **Action 2 (Upload)**：定时、手动或在 Action 1 完成后自动联动上传至指定 Gist。
7. **Gist 同名覆写**：扫描所有生成的代理文件，保持原文件名上传，自动覆写更新 Gist 现有内容。

---

## 文件与格式规范

### 1. 文件命名
```text
proxies/
├── US-SOCKS5.txt
├── US-HTTP.txt
├── DE-SOCKS5.txt
├── JP-HTTPS.txt
└── ...
```

### 2. 单行格式
```text
<protocol>://<ip>:<port>#<COUNTRY_CODE>-<PROTOCOL>-<INDEX>
```
示例：
- `US-SOCKS5.txt`:
  ```text
  socks5://45.61.129.165:9050#US-SOCKS5-1
  socks5://184.170.249.65:4145#US-SOCKS5-2
  ```
- `US-HTTP.txt`:
  ```text
  http://142.93.202.130:3128#US-HTTP-1
  http://45.91.248.107:80#US-HTTP-2
  ```

---

## 目录结构

```text
proxy-list/
├── .github/
│   └── workflows/
│       ├── fetch-proxies.yml        # Action 1: 抓取与格式化代理列表
│       └── upload-to-gist.yml       # Action 2: 上传/覆写到 Gist
├── proxies/                         # 生成的代理文件存放目录 (默认仅包含 .gitkeep)
│   └── .gitkeep
├── scripts/
│   ├── fetch_proxies.py             # 多协议抓取、校验与格式化脚本 (Python 3)
│   └── upload_to_gist.py            # Gist 上传覆写脚本 (Python 3)
├── tests/
│   ├── test_fetch_proxies.py        # 抓取逻辑单元测试
│   └── test_upload_to_gist.py       # 上传逻辑单元测试
├── .gitignore
└── README.md                        # 项目说明文档
```

---

## 快速开始与配置

### 1. 配置 GitHub Secrets & Variables

在 GitHub 仓库中，进入 **Settings** -> **Secrets and variables** -> **Actions**：

| 名称 | 类型 | 必需 | 说明 |
| :--- | :--- | :--- | :--- |
| `GIST_TOKEN` | **Repository secret** | **必需** | 具有 `gist` 权限的 GitHub Personal Access Token (PAT) |
| `PROXYSCRAPE_TOKEN` | **Repository secret** | 可选 | 你的 ProxyScrape.com API Token / Key |
| `GIST_URL` | **Repository variable** 或 **Secret** | **必需** | 你的 Gist 链接，例如 `https://gist.github.com/<user>/<gist-id>` |

> **提示：如何获取 GIST_TOKEN？**
> 1. 打开 GitHub -> 点击右上角头像 -> **Settings** -> **Developer Settings** -> **Personal access tokens** -> **Tokens (classic)**。
> 2. 点击 **Generate new token**，勾选 `gist` 权限。
> 3. 复制生成的 Token，并在本仓库 Secrets 中添加为 `GIST_TOKEN`。

---

### 2. 自定义国家与协议列表

在 `.github/workflows/fetch-proxies.yml` 中可直接修改默认环境参数：
```yaml
env:
  DEFAULT_COUNTRIES: "US,DE,GB,FR,JP,HK,SG" # 以逗号分隔，支持 ALL
  DEFAULT_PROTOCOLS: "socks5"             # 可改为 "socks5,socks4,http,https" 等
```

---

## 工作流说明

### Action 1: 抓取与格式化代理列表 (`fetch-proxies.yml`)
* **定时执行**：默认每 6 小时自动执行一次（`cron: "0 */6 * * *"`）。
* **手动执行**：
  1. 进入仓库的 **Actions** 标签页。
  2. 点击左侧 **Fetch Proxies**。
  3. 点击 **Run workflow**，支持自定义国家列表（如 `US,JP`）和协议列表（如 `socks5,http`）。
* **执行结果**：自动提交最新代理列表到 `proxies/` 目录，并打包上传为 GitHub Artifact。

### Action 2: 同步覆写至 GitHub Gist (`upload-to-gist.yml`)
* **定时执行**：默认每 6 小时自动执行一次（`cron: "15 */6 * * *"`）。
* **联动触发**：当 Action 1 执行成功后，本工作流会自动触发同步。
* **手动执行**：
  1. 进入仓库的 **Actions** 标签页。
  2. 点击左侧 **Upload Proxies to Gist**。
  3. 点击 **Run workflow**，支持临时覆盖 Gist URL 或文件筛选关键词。
* **执行结果**：自动扫描 `proxies/` 目录下匹配关键词（如 `socks5,socks4,http,https`）的文件，保持原文件名覆写更新到指定的 Gist。

---

## 本地开发与测试

### 1. 运行单元测试
```bash
python -m unittest discover tests
```

### 2. 本地抓取测试
```bash
# 抓取美国和德国的 SOCKS5 和 HTTP 代理
python scripts/fetch_proxies.py --countries US,DE --protocols socks5,http --output-dir proxies

# 若有 ProxyScrape Token
python scripts/fetch_proxies.py --countries US --protocols socks5 --token YOUR_TOKEN --output-dir proxies
```

### 3. 本地上传测试
```bash
python scripts/upload_to_gist.py \
  --gist-url "https://gist.github.com/<user>/<gist-id>" \
  --token "ghp_xxxxxxxxxxxx" \
  --dir proxies \
  --keywords "socks5,socks4,http,https"
```

---

## 注意事项
1. **GitHub API 限制**：每个 Gist 单个文件大小上限为 10MB，每次更新在一次 PATCH 请求内原子化完成。
2. **ProxyScrape 节点变动**：公开代理节点存在存活时效，建议保持 3~6 小时定时抓取一次以维持最新可用性。
