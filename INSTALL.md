# 安装 paper-research（面向 AI agent / 手动）

你是 AI agent，用户让你安装 `paper-research`。本文档即安装流程，请按顺序执行。每一步都可安全重跑，且都写明了失败时的处理。命令为 POSIX shell（macOS / Linux），需要 Windows 特例的步骤附有说明。

`paper-research` 是统一多源学术文献检索 skill：一次查询跨 **OpenAlex / CrossRef / Semantic Scholar / PubMed / Scopus / Web of Science** 六大库检索，自动去重、按引用/日期排序、支持 JSON 导出，可按 **SCI 中科院分区**与摘要筛选。核心检索**零第三方依赖**（纯 Python 标准库）；仅 WoS 截图+OCR 兜底需要可选依赖。

整个安装分为六步：

1. 找到当前 harness 的 skill 目录。
2. 把 `paper-research` 文件夹放入其中。
3. 安装 Python 依赖（可选）。
4. 配置凭据（可选，默认四个源免 key）。
5. 运行前配置（首次运行自动生成，无需手动填路径）。
6. 验证。

---

## 第 1 步：找到当前 harness 的 skill 目录

skill 是 harness 启动时读取的文件夹，各 harness 从固定位置读取：

| Harness | Skill 目录（`TARGET`） |
| :-- | :-- |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| Pi, OpenCode | `~/.agents/skills/` |

安装到用户主目录下的这个**全局**目录，使 skill 在每个项目都可用。除非用户明确要求仅限当前项目，否则**不要**装到项目本地 `.claude/skills`。

不确定当前是哪个 harness 时，按已存在的配置目录判断：

```bash
ls -d ~/.claude ~/.codex ~/.agents 2>/dev/null
```

- `~/.claude` 存在 → 用 `~/.claude/skills/`
- `~/.codex` 存在 → 用 `~/.codex/skills/`
- `~/.agents` 存在 → 用 `~/.agents/skills/`

创建目录作为安装目标：

```bash
mkdir -p ~/.claude/skills   # 替换为你对应 harness 的 TARGET
```

**若失败**：权限错误说明你指向的目录不可写。确认路径在用户主目录下（`echo $HOME`），不是系统路径。

> **Windows**：`~` 即用户配置文件。目录为
> `%USERPROFILE%\.claude\skills\`、`%USERPROFILE%\.codex\skills\`、
> `%USERPROFILE%\.agents\skills\`。用 PowerShell `mkdir "$env:USERPROFILE\.claude\skills"` 创建。

---

## 第 2 步：把 skill 文件夹放入 skill 目录

skill 即本仓库中的 `paper-research` 文件夹：`SKILL.md`（AI 执行指令）、`manifest.yaml`（元数据）、`README.md`、`INSTALL.md`（本文档）、`scripts/`（核心检索 + OCR 兜底脚本）、`resources/`（配置模板 + 分区数据）、`docs/`、`references/`。把整个文件夹复制（或符号链接）到 `TARGET`。

### 方式 A：从仓库复制（不依赖额外工具）

```bash
TARGET=~/.claude/skills                    # 替换为你对应 harness 的目录
rm -rf "$TARGET/paper-research"
cp -R "/path/to/paper-research" "$TARGET/paper-research"
```

重复执行会覆盖旧安装，等价于刷新。

**若失败**：
- 源路径错误 → 确认 `paper-research` 文件夹的真实位置。
- 复制后确认文件落位：
  ```bash
  ls "$TARGET/paper-research"/SKILL.md "$TARGET/paper-research"/scripts/paper_research.py
  ```
  若 `SKILL.md` 或 `scripts/` 缺失，说明复制目标错误，重跑 `cp` 行并检查 `TARGET`。

### 方式 B：符号链接（仅 macOS / Linux）

保留仓库源目录、在 `TARGET` 建软链，之后 `git pull` 即自动更新：

```bash
ln -s /path/to/paper-research ~/.claude/skills/paper-research
```

> **Windows**：PowerShell 用 `Copy-Item -Recurse -Force "F:\projects\paper-research" "$env:USERPROFILE\.claude\skills\paper-research"`。

---

## 第 3 步：安装 Python 依赖

- **核心检索**（`paper_research.py`）：仅 Python 标准库，**无需安装任何包**。需 Python 3.9+。
- **WoS 截图 OCR 兜底**（`wos_snapshot.py`，可选）：需要 `playwright` + `rapidocr_onnxruntime`。

检查当前环境：

```bash
python3 --version
python3 -c "import playwright, rapidocr_onnxruntime; print('ocr deps ok')" 2>/dev/null || echo "ocr deps missing (optional)"
```

按需安装：

```bash
pip install playwright rapidocr_onnxruntime
```

首次运行 `wos_snapshot.py` 时，Playwright 优先使用系统 Chrome/Edge（自动查找），或 `playwright install chromium` 安装自带内核。

**若失败**：`pip: command not found` 说明 Python 未加入 PATH——从 python.org 安装 Python 3.9+ 后重试；权限错误说明用户 site 不可写，用 `pip install --user ...`。

> **Windows**：`python3` 可能是 `python`。用 `python --version` 与 `python -m pip install playwright rapidocr_onnxruntime`。

---

## 第 4 步：配置凭据（可选，默认四个源免 key）

OpenAlex / CrossRef / Semantic Scholar / PubMed **四个源免费、无需 key**；Scopus 与 WoS 需要 key，缺 key 时脚本自动跳过。脚本从多个位置自动发现凭据（环境变量 → `resources/config/config.env` → `~/.config/pybliometrics.cfg` → `~/.config/lit-dl/credentials.json`），**不填 key 也能先跑通免费源**。

| 源 | 是否需 key | 建议配置 |
| :-- | :-- | :-- |
| OpenAlex | 否 | 可选 `OPENALEX_MAILTO`（进 polite pool 提升额度） |
| CrossRef | 否 | 可选 `CROSSREF_MAILTO` |
| Semantic Scholar | 否 | 可选 `S2_API_KEY`（提升共享限流） |
| PubMed | 否 | 可选 `NCBI_API_KEY`（限流 3→10 rps） |
| Scopus | **是** | `SCOPUS_API_KEY` |
| WoS | **是** | `WOS_API_KEY` |

### 4a. 推荐：填 `resources/config/config.local.env`

复制模板（`config.local.env` 已被 `.gitignore` 忽略，不会入库）：

```bash
cd "<TARGET>/paper-research"
cp resources/config/config.env resources/config/config.local.env
```

用编辑器填好 `SCOPUS_API_KEY=` / `WOS_API_KEY=` / `OPENALEX_MAILTO=` 等行。

> **Windows (PowerShell)**：`Copy-Item resources\config\config.env resources\config\config.local.env`

### 4b. 或：环境变量（优先于配置文件）

```bash
export SCOPUS_API_KEY="..."
export WOS_API_KEY="..."
export OPENALEX_MAILTO="you@example.com"
```

**持久化**（Windows PowerShell）：

```powershell
[System.Environment]::SetEnvironmentVariable('SCOPUS_API_KEY', '...', 'User')
[System.Environment]::SetEnvironmentVariable('WOS_API_KEY', '...', 'User')
[System.Environment]::SetEnvironmentVariable('OPENALEX_MAILTO', 'you@example.com', 'User')
```

Scopus / WoS key 的申请步骤见 `docs/Scopus_API申请与使用指南.md` 与 `docs/WoS_API申请与使用指南.md`。

---

## 第 5 步：运行前配置（首次运行自动生成）

本 skill **没有**需要手动填的路径配置。运行时会自动生成两个本地配置（均已 `.gitignore`，不入库）：

- `resources/config/sources.env` —— 首次运行时交互选择文献库，询问"是否保存为默认"，选 `y` 生成。
- `resources/config/preferences.env` —— 首次运行时交互选择摘要筛选偏好（1-4）与 SCI 分区偏好（0-4）后生成。

用户可在首次交互中直接选择，或稍后编辑，或用 `--sources ... --save-sources` / `--filter` / `--zone` 临时覆盖。

---

## 第 6 步：验证

```bash
cd "<TARGET>/paper-research"

# 版本（应输出 paper-research 1.0.0）
python scripts/paper_research.py --version

# 检查 key 配置（四个免费源显示 free，Scopus/WoS 显示是否 set）
python scripts/paper_research.py --check-keys

# 实弹一次免费源检索（无 key 也能跑）
python scripts/paper_research.py "silver nanowire electrode" --sources openalex,crossref --sort cited --limit 5

# 可选：WoS OCR 兜底自测
python scripts/wos_snapshot.py --selftest
```

**若失败**：
- `ModuleNotFoundError` → 第 3 步依赖缺失（仅 OCR 路径需要）。
- 终端中文乱码 → Windows 下加 `PYTHONIOENCODING=utf-8` 前缀运行。
- 某源报错到 stderr → 单源失败不影响其余源（缺 key 自动跳过属正常）。

---

## 完成

skill 已安装。重启 Claude Code（或 `/clear`）使新 skill 生效。此后用户只需说：

> 帮我搜一下关于 X 的论文

AI 会自动运行 `python scripts/paper_research.py "<query>"` 跨库检索。用法详见 `README.md`。
