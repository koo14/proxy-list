# ProxyScrape SOCKS5 Proxy List & Gist Auto-Sync

[![Fetch SOCKS5 Proxies](https://github.com/USER/REPO/actions/workflows/fetch-proxies.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/fetch-proxies.yml)
[![Upload SOCKS5 Proxies to Gist](https://github.com/USER/REPO/actions/workflows/upload-to-gist.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/upload-to-gist.yml)

自动化从 [proxyscrape.com](https://proxyscrape.com) 抓取指定国家/地区的 SOCKS5 代理列表，进行标准格式化，并通过 GitHub Actions 自动覆写同步至 GitHub Gist。

---

## 目录
- [项目特性](#项目特性)
- [文件与格式规范](#文件与格式规范)
- [目录结构](#目录结构)
- [快速开始与配置](#快速开始与配置)
  - [1. 配置 GitHub Secrets & Variables](#1-配置-github-secrets--variables)
  - [2. 自定义国家列表](#2-自定义国家列表)
- [工作流说明](#工作流说明)
  - [Action 1: 抓取与格式化代理列表 (fetch-proxies.yml)](#action-1-抓取与格式化代理列表-fetch-proxiesyml)
  - [Action 2: 同步覆写至 GitHub Gist (upload-to-gist.yml)](#action-2-同步覆写至-github-gist-upload-to-gistyml)
- [本地开发与测试](#本地开发与测试)
- [注意事项](#注意事项)

---

## 项目特性

1. **多国家支持**：在 Action 配置文件或手动触发时轻松指定国家代码（如 `US,DE,GB,FR,JP,HK,SG` 或 `ALL`）。
2. **标准命名与格式**：
   - 文件名：`COUNTRY_CODE-SOCKS5.txt`（如 `US-SOCKS5.txt`、`DE-SOCKS5.txt`）。
   - 内容格式：`socks5://xxx:yyy #COUNTRY_CODE-SOCKS5-Number`。
3. **ProxyScrape Token 支持**：支持传入 ProxyScrape API Token/Key，未配置时自动回退到公开接口。
4. **两套独立 GitHub Actions**：
   - **Action 1 (Fetch)**：定时或手动抓取并提交到仓库 `proxies/` 目录。
   - **Action 2 (Upload)**：定时、手动或在 Action 1 完成后自动联动上传至指定 Gist。
5. **Gist 同名覆写**：扫描所有包含 `socks5` 关键词的文件，保持原文件名上传，自动覆写更新 Gist 现有内容。

---

## 文件与格式规范

### 1. 文件命名
```text
proxies/
├── US-SOCKS5.txt
├── DE-SOCKS5.txt
├── JP-SOCKS5.txt
└── ...
```

### 2. 单行格式
```text
socks5://<ip>:<port> #<COUNTRY_CODE>-SOCKS5-<INDEX>
```
示例 (`US-SOCKS5.txt`):
```text
socks5://45.61.129.165:9050 #US-SOCKS5-1
socks5://184.170.249.65:4145 #US-SOCKS5-2
socks5://216.68.128.121:4145 #US-SOCKS5-3
```

---

## 目录结构

```text
proxy-list/
├── .github/
│   └── workflows/
│       ├── fetch-proxies.yml        # Action 1: 抓取与格式化代理列表
│       └── upload-to-gist.yml       # Action 2: 上传/覆写到 Gist
├── proxies/                         # 生成的代理文件存放目录
│   └── .gitkeep
├── scripts/
│   ├── fetch_proxies.py             # 抓取、校验与格式化脚本 (Python 3)
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

### 2. 自定义国家列表

若需修改默认抓取的国家代码，可以直接在 `.github/workflows/fetch-proxies.yml` 中的 `DEFAULT_COUNTRIES` 修改：
```yaml
env:
  DEFAULT_COUNTRIES: "US,DE,GB,FR,JP,HK,SG" # 以逗号分隔，支持 ALL
```

---

## 工作流说明

### Action 1: 抓取与格式化代理列表 (`fetch-proxies.yml`)
* **定时执行**：默认每 6 小时自动执行一次（`cron: "0 */6 * * *"`）。
* **手动执行**：
  1. 进入仓库的 **Actions** 标签页。
  2. 点击左侧 **Fetch SOCKS5 Proxies**。
  3. 点击 **Run workflow**，可按需输入国家列表（留空则使用默认配置）。
* **执行结果**：自动提交最新代理列表到 `proxies/` 目录，并打包上传为 GitHub Artifact。

### Action 2: 同步覆写至 GitHub Gist (`upload-to-gist.yml`)
* **定时执行**：默认每 6 小时自动执行一次（`cron: "15 */6 * * *"`，稍晚于 Action 1）。
* **联动触发**：当 Action 1 执行成功后，本工作流会自动触发同步。
* **手动执行**：
  1. 进入仓库的 **Actions** 标签页。
  2. 点击左侧 **Upload SOCKS5 Proxies to Gist**。
  3. 点击 **Run workflow**，支持临时覆盖 Gist URL。
* **执行结果**：自动扫描 `proxies/` 目录下所有包含 `socks5` 命名的文件，保持原文件名覆写更新到指定的 Gist。

---

## 本地开发与测试

### 1. 运行单元测试
项目无额外三方依赖，使用 Python 3.10+ 标准库即可：
```bash
python -m unittest discover tests
```

### 2. 本地抓取测试
```bash
# 抓取美国和德国的 SOCKS5 代理
python scripts/fetch_proxies.py --countries US,DE --output-dir proxies

# 若有 token
python scripts/fetch_proxies.py --countries US,DE --token YOUR_TOKEN --output-dir proxies
```

### 3. 本地上传测试
```bash
python scripts/upload_to_gist.py \
  --gist-url "https://gist.github.com/<user>/<gist-id>" \
  --token "ghp_xxxxxxxxxxxx" \
  --dir proxies
```

---

## 注意事项
1. **GitHub API 限制**：每个 Gist 单个文件大小上限为 10MB，每次更新在一次 PATCH 请求内原子化完成。
2. **ProxyScrape 节点变动**：公开代理节点存在存活时效，建议保持 3~6 小时定时抓取一次以维持最新可用性。
