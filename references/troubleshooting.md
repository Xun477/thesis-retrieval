# 故障排查与注意事项（Troubleshooting）

> 仅在遇到对应故障、或需要确认运行细节时打开本文件。

## 目录

- [API key 相关](#api-key-相关)
  - [缺 key 报错](#缺-key-报错)
  - [key 已配置但仍报缺 key](#key-已配置但仍报缺-key)
- [请求与网络](#请求与网络)
  - [HTTP 429 限流](#http-429-限流)
  - [TLS/SSL 证书错误](#tlsssl-证书错误)
  - [网络超时 / 单源失败](#网络超时--单源失败)
- [结果异常](#结果异常)
  - [结果乱码 / 中文显示异常](#结果乱码--中文显示异常)
  - [无结果或结果过少](#无结果或结果过少)
  - [被引数缺失或为 0](#被引数缺失或为-0)
- [安装与运行](#安装与运行)
  - [skill 未出现在可用列表](#skill-未出现在可用列表)
  - [交互菜单乱码](#交互菜单乱码)
- [WoS 截图 OCR（wos_snapshot.py）](#wos-截图-ocrwos_snapshotpy)
  - [浏览器没打开](#浏览器没打开)
  - [跳到登录页 / 识别空白](#跳到登录页--识别空白)
  - [识别结果乱码或不完整](#识别结果乱码或不完整)

---

## API key 相关

### 缺 key 报错

**现象**：运行时报 `Scopus API key missing` / `WoS API key missing`，或 `--check-keys` 显示 `[missing]`。

**原因**：scopus / wos 必须配置 key；其余四源免费免 key。

**处理**：
- 在 `resources/config/config.env` 填入 `SCOPUS_API_KEY` / `WOS_API_KEY`，或设同名环境变量。
- 申请指南见 `docs/Scopus_API申请与使用指南.md`、`docs/WoS_API申请与使用指南.md`。
- 缺 key 的源会自动跳过，其余源继续工作，无需重试。

### key 已配置但仍报缺 key

**现象**：`--check-keys` 显示 `[missing]`，但确认已填 key。

**原因**：key 发现顺序是 环境变量 → `resources/config/config.env` → 其他。可能：文件路径不对、变量名拼错、文件是旧位置 `config/config.env`。

**处理**：
- 确认文件在 `resources/config/config.env`（v0.4.1 起移入 resources，旧位置不再读取）。
- 确认变量名：`SCOPUS_API_KEY`、`WOS_API_KEY`、`S2_API_KEY`、`NCBI_API_KEY`、`OPENALEX_MAILTO`。
- 环境变量优先级最高，若环境里设了空值会覆盖文件。

---

## 请求与网络

### HTTP 429 限流

**现象**：`semantic_scholar: HTTP 429`（无 key 时共享限流，高峰期常见）。

**原因**：Semantic Scholar 无 key 使用全局共享额度；PubMed 无 key 限 3 rps。

**处理**：
- 脚本自动重试 3 次（指数退避）；高峰期稍后重试即可。
- 稳定使用：申请免费 `S2_API_KEY`（[申请页](https://www.semanticscholar.org/product/api)）填入 config；NCBI key 同理提升到 10 rps。
- 也可临时排除该源：`--sources` 不带 semantic_scholar。

### TLS/SSL 证书错误

**现象**：请求抛 `ssl.SSLError` / `CERTIFICATE_VERIFY_FAILED`。

**原因**：本机 TLS 环境异常（历史版本曾为绕 pybliometrics bug 全局关闭证书校验，已改默认校验）。

**处理**：
- 脚本已内置定向 fallback：SSL 失败自动用宽松上下文重试一次，一般无需干预。
- 若持续失败，检查系统时间/CA 证书库。

### 网络超时 / 单源失败

**现象**：某源报 `request failed after 3 attempts`，其余源正常。

**原因**：网络抖动 / 该源限流 / 服务端 5xx。

**处理**：单源失败不影响整体，结果照常返回并到 stderr 报错；稍后单独重试该源。

---

## 结果异常

### 结果乱码 / 中文显示异常

**现象**：终端输出中文/说明文字变 `???` 或乱码。

**原因**：Windows 终端（cmd）默认 GBK 编码，脚本输出 UTF-8。

**处理**：功能不受影响；换用 Windows Terminal / 设置 `chcp 65001`，或 `--out` 导出 JSON（UTF-8 正确）。

### 无结果或结果过少

**现象**：提示无结果，或某源 0 条。

**原因**：查询词过窄 / 引号过多 / 该源覆盖有限。

**处理**：
- 换关键词、减少引号、拆短语。
- 加 `--sources` 扩大库范围；用 `--limit` 提高条数。
- 中文文献：OpenAlex 对 CNKI 收录部分覆盖，但中文核心库无 API（见 `references/chinese-sources.md`）。

### 被引数缺失或为 0

**现象**：`cit=0` 或 `cit=?`。

**原因**：PubMed 不提供被引数（恒为 None，显示 0）；Crossref/OpenAlex 对部分条目无数据；WoS 需 Institutional Plan 才含被引。

**处理**：`cit=0` 不代表无人引；对比被引数时优先用 OpenAlex/Crossref/Semantic Scholar 源，并注意各源被引口径不同。

---

## 安装与运行

### skill 未出现在可用列表

**现象**：Claude Code 里看不到 paper-research 技能。

**原因**：未安装或链接失效。

**处理**：运行 `bash install.sh`（在 `~/.claude/skills/` 建符号链接），重启 Claude Code 或 `/clear`。

### 交互菜单乱码

**现象**：不传 `--sources` 时多选菜单文字乱码。

**原因**：终端编码问题（同"结果乱码"）。

**处理**：菜单功能不受影响；脚本化场景直接传 `--sources` 跳过菜单。

---

## WoS 截图 OCR（wos_snapshot.py）

### 浏览器没打开

**现象**：`python scripts/wos_snapshot.py "<url>"` 报错，浏览器未弹出。

**原因**：未安装 `playwright`，或系统没有 Chrome/Edge，且未装 Playwright 自带内核。

**处理**：
- `pip install playwright`，且系统有 Chrome/Edge（脚本自动查找 `C:\Program Files\...\chrome.exe` / `msedge.exe`）。
- 无系统浏览器时：`python -m playwright install chromium`。

### 跳到登录页 / 识别空白

**现象**：脚本输出了"Sign in"等文字，或 `text` 为空。

**原因**：WoS 需要登录；或页面是登录墙。

**处理**：先在浏览器里登录 WoS（脚本用持久化用户目录 `%TEMP%\wos-snapshot-chrome-profile`，登录一次后续复用）。
登录态失效时重登即可。脚本不提供绕过登录/反爬能力，必要时人工截图 + `--ocr-only`。

### 识别结果乱码或不完整

**现象**：`--selftest` 乱码，或中文/字段识别不完整。

**原因**：Windows 终端编码（同"结果乱码"）；WoS 布局多变，OCR 是"尽力而为"。

**处理**：
- 乱码：`PYTHONIOENCODING=utf-8` 或换 Windows Terminal；功能不受影响。
- 字段缺失：优先用 `--out` JSON 的 `text` 原始文本人工核对；WoS 页面改版时更新 `parse_record_text`。
- OCR 质量差：确保截图清晰、放大页面后再截；或直接用 DOM 文本路径（不触发 OCR）。
