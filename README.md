# thesis-retrieval (v1.1.0)

统一多源学术文献检索 Skill。一次查询跨 **OpenAlex / CrossRef / Semantic Scholar / PubMed / Scopus / Web of Science** 六个学术库检索，自动去重、按引用/日期排序，支持 JSON 导出。WoS 独有文献（其他库查不到、也无 DOI）可用截图+OCR 兜底抓取。支持按 **SCI 中科院分区**筛选。

## 安装

面向 AI agent / 手动两种方式的完整安装指引见 **[INSTALL.md](INSTALL.md)**。

##### AI agent 安装

**交给你的 AI**，把这句话发给它：

> 按本仓库的 INSTALL.md 安装并配置 thesis-retrieval skill，完成后运行体检（--version / --check-keys）并把结果告诉我。

##### 手动安装

简要步骤：

1. 把 `thesis-retrieval` 文件夹复制到 skill 目录（Claude Code 为 `~/.claude/skills/`，Windows 为 `%USERPROFILE%\.claude\skills\`）
2. 核心检索零依赖，无需装包；WoS 截图 OCR 兜底才需 `pip install playwright rapidocr_onnxruntime`
3. 配置凭据（可选）：复制 `resources/config/config.env` → `resources/config/config.local.env` 填写，或用环境变量 `SCOPUS_API_KEY` / `WOS_API_KEY` / `OPENALEX_MAILTO`。OpenAlex / CrossRef / Semantic Scholar / PubMed **四源免 key 直接可用**
4. 运行配置：首次运行交互生成 `sources.env` 与 `preferences.env`，无需手动填路径

> **开源协议：** 本 skill 以 **MIT** 协议发布，见 [LICENSE](LICENSE)。

> v1.1.0：首次运行初始化改为「三问式」（选文献库 / 摘要筛选 / SCI 分区，二三问两阶段），选完自动写 config；修复 save_filter_pref 覆盖分区配置的 bug。
> v1.0.1：项目/skill 名称统一为 thesis-retrieval（脚本、manifest、文档同步改名）。
> v1.0.0：正式发布版——补全 INSTALL.md 安装指引，文档与版本号同步 1.0.0。
> v0.9.1：修复 `--save-sources` / `--filter` / `--zone-mode` 持久化失效；README 补 Windows 编码提示。
> v0.9.0：新增 SCI 中科院分区筛选（`--zone`，本地映射表 `resources/data/journal_zones.json`，偏好可持久化）。
> v0.8.0：新增 WoS 截图+OCR 兜底脚本 `scripts/wos_snapshot.py`（Playwright 开浏览器 → 截图 → RapidOCR 识别）。
> v0.7.0：新增摘要提取与按摘要筛选（初始化时选择偏好，可持久化）。
> v0.6.0：修复 WoS 布尔运算符（OR/AND）导致的 HTTP 400，自动拆分顶层 OR。
> v0.5.1：WoS API 人工审核提醒（周期长，可先用其他库）。
> v0.5.0：首次初始化选择文献库并持久化配置。
> v0.4.0：新增 docs/ API 申请与使用指南（Scopus / WoS）。
> v0.3.2：SKILL.md 改为纯 AI 指令风格。
> v0.3.1：精简 SKILL.md，新增 `--list-sources` 运行时自查。
> v0.3.0：新增 CrossRef、Semantic Scholar、PubMed 三个免费无需 key 的检索源。

## 为什么有这个 skill

原 `nature-academic-search` 依赖 MCP server + pybliometrics，在本机遇到两个问题：
1. **pybliometrics SSL 错误**导致 Scopus 不可用（`SSLError`）
2. **缺 WoS** 检索能力

`thesis-retrieval` 用直接 HTTP 调用替代 pybliometrics（绕开 SSL bug），并新增 **WoS Starter API** **、CrossRef、Semantic Scholar、PubMed** 直连。六个源合并为一个 CLI。

> 安全说明：旧版脚本为绕开 SSL bug 曾**对所有请求关闭 TLS 证书校验**（中间人攻击风险）。
> 现改为**默认校验证书**，仅在该请求本身触发 SSL 错误时，用宽松上下文自动重试一次作为定向 fallback。

## 快速开始

```bash
# 六库联合检索
python scripts/thesis_retrieval.py "silver nanowire liquid metal electrode" --sources openalex,crossref,semantic_scholar,pubmed,scopus,wos

# 不指定 --sources：启动前交互式多选要检索哪些库（可多选 / all / 回车默认全部可用）
python scripts/thesis_retrieval.py "silver nanowire"

# 只查 WoS 按引用排序
python scripts/thesis_retrieval.py "silver nanowire" --sources wos --sort cited

# 检查 key 配置
python scripts/thesis_retrieval.py --check-keys

# 查看每个源的覆盖/凭据/查询语法（运行时自查）
python scripts/thesis_retrieval.py --list-sources

# 查看版本
python scripts/thesis_retrieval.py --version
```

> **Windows 提示**：若终端中文乱码（GBK 编码），加 `PYTHONIOENCODING=utf-8` 前缀运行：
> `PYTHONIOENCODING=utf-8 python scripts/thesis_retrieval.py "查询词"`。

## 依赖

- **核心检索**（`thesis_retrieval.py`）：仅 Python 标准库（urllib/json/ssl/argparse），**零第三方依赖**。
- **WoS 截图 OCR 兜底**（`wos_snapshot.py`，可选）：`pip install playwright rapidocr_onnxruntime`；首次运行 `playwright` 需系统 Chrome/Edge（推荐，脚本自动查找），或 `playwright install chromium` 安装自带内核。

## API key

脚本自动从以下位置发现 key（无需手动配置）：

| 源 | key 来源 |
|----|------|
| Scopus | 环境变量 `SCOPUS_API_KEY` → `resources/config/config.env` → `~/.config/pybliometrics.cfg` → `~/.config/lit-dl/credentials.json` |
| WoS | 环境变量 `WOS_API_KEY` → `resources/config/config.env` → `~/.config/lit-dl/credentials.json` |
| OpenAlex | 免 key，可用 `OPENALEX_MAILTO` 提升额度 |
| CrossRef | 免 key，可用 `CROSSREF_MAILTO`（Polite Pool） |
| Semantic Scholar | 免 key，可用 `S2_API_KEY`（可选，提升共享限流） |
| PubMed | 免 key，可用 `NCBI_API_KEY`（可选，提升限流到 10 rps） |

Scopus / WoS key 的申请与使用步骤见 [`docs/Scopus_API申请与使用指南.md`](docs/Scopus_API申请与使用指南.md) 和 [`docs/WoS_API申请与使用指南.md`](docs/WoS_API申请与使用指南.md)。

## WoS 独有文献兜底（截图 + OCR）

部分 WoS 收录的文献**没有 DOI**、其他库（OpenAlex/CrossRef/Semantic Scholar/PubMed/Scopus）查不到；WoS Starter API 也不返回摘要。此时 API 路径无解，用浏览器截图 + OCR 兜底：

```bash
# 依赖（首次）
pip install playwright rapidocr_onnxruntime

# 自测 OCR 是否可用
python scripts/wos_snapshot.py --selftest

# 打开 WoS 结果/详情页 URL，抓取并识别文字（AI 助手执行）
python scripts/wos_snapshot.py "https://www.webofscience.com/wos/woscc/summary/xxxx" --out wos_snapshot.json

# 已有截图，仅做 OCR
python scripts/wos_snapshot.py --ocr-only --image screenshot.png
```

- 需要先在浏览器里**登录 WoS**；脚本复用登录态（Playwright 持久化用户目录），不绕过登录/反爬。
- 输出：页面文本 + 结构化字段（标题/作者/期刊/年份/DOI/被引）。WoS 布局多变，识别为"尽力而为"，AI 应结合原始文本判断。
- 设计思路借鉴：Zotero Connector 的 `Web of Science.js` 翻译器（读取页面表单、按 `RECORD_` 记录块抓取）+ 开源 WoS 抓取项目（登录态 + 页面解析）。详见 `docs/WoS截图OCR兜底说明.md`。

## 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `query` | — | 检索词（位置参数） |
| `--sources` | 保存的配置 | 参与**检索**的源，逗号分隔：`openalex,crossref,semantic_scholar,pubmed,scopus,wos`。不传时用保存配置（首次运行会交互初始化并自动保存） |
| `--save-sources` | — | 把本次选择写入 `resources/config/sources.env` 作为默认 |
| `--source` | — | 只**显示**来自某源的结果，不影响检索范围 |
| `--limit` | 10 | 每源最大结果数（Scopus ≤25，其他 ≤50） |
| `--sort` | `relevance` | 排序：`relevance` / `cited` / `date` |
| `--out` | — | 写 JSON 文件（始终含 abstract 字段） |
| `--abstracts` | — | 文本输出也打印摘要 |
| `--filter` | 保存的偏好 | 摘要筛选：`always`（以后都是）/ `once`（仅本次）/ `no`（这次不用）/ `never`（以后都不用） |
| `--zone` | 保存的偏好 | SCI 中科院分区下限：`1`/`2`/`3`/`4`，只保留分区 ≤ 该值的文献（1 区最高） |
| `--zone-mode` | 保存的偏好 | 分区筛选模式：`always`（保存为默认，以后都这样）/ `once`（仅本次）/ `off`（本次不用） |
| `--check-keys` | — | 检查 API key 配置后退出 |
| `--list-sources` | — | 列出各源覆盖/凭据/查询语法后退出 |
| `--version` | — | 显示版本号（1.1.0） |

注意：**`--sources` 控制查哪些库，`--source` 只过滤显示**。

## 文献库配置（持久化默认）

- **首次运行**：未保存配置时，交互选择文献库，选完**自动保存**为默认（`resources/config/sources.env`），不再单独询问。
- **之后运行**：直接用保存的库（`resources/config/sources.env`），不再询问。
- **想换默认库**：编辑 `resources/config/sources.env` 的 `SOURCES=` 行，或删除该文件重新初始化，或 `--sources ... --save-sources` 覆盖。
- 完整说明见 [`docs/文献库配置说明.md`](docs/文献库配置说明.md)。

## 摘要筛选（按摘要判断是否符合需求）

- **首次运行**：先问"是否按摘要自动筛选？[是/不是]"，选"是"后再问"仅此一次/以后都是"，选择自动持久化到 `resources/config/preferences.env`。
- **筛选时 AI 行为**：逐条读 abstract，标注 `[符合] / [不确定] / [排除]`。
- **摘要覆盖**：OpenAlex/CrossRef/Semantic Scholar 免费返回；Scopus/PubMed/WoS 默认无（跨源按 DOI 兜底补齐）。
- **想改偏好**：编辑 `resources/config/preferences.env` 的 `FILTER_BY_ABSTRACT=` 行（always/once/no/never），或删除重选，或 `--filter` 临时覆盖。
- 完整说明见 [`docs/摘要筛选说明.md`](docs/摘要筛选说明.md)。

## SCI 分区筛选（中科院分区）

- **首次运行**：先问"只保留哪个区及以上？[一区/二区/三区/四区/全部]"，选分区后再问"仅此一次/以后都是"，选择自动持久化到 `resources/config/preferences.env`。
- **分区数据**：本地映射表 `resources/data/journal_zones.json`（期刊名 → 分区 1-4）。需按研究方向维护，见 [`docs/SCI分区筛选说明.md`](docs/SCI分区筛选说明.md)。
- **筛选行为**：只保留分区 ≤ `ZONE_MIN` 的文献；未知期刊**保留**并标注 `分区=?`，不误删。
- **临时覆盖**：`--zone 1 --zone-mode once`（仅本次）、`--zone 2 --zone-mode always`（保存为默认）、`--zone-mode off`（本次不用）。
- **想改偏好**：编辑 `resources/config/preferences.env` 的 `ZONE_FILTER=` / `ZONE_MIN=` 行，或删除重选。

## 查询语法

- **OpenAlex**：普通关键词即 title+abstract 全文搜索；加引号做精确短语。
- **CrossRef**：`query.bibliographic` 书目检索，接受普通关键词。
- **Semantic Scholar**：普通关键词即可。
- **PubMed**：普通关键词传给 NCBI esearch，支持字段标签/布尔运算。
- **Scopus**：接受 Scopus 高级检索语法，如 `TITLE-ABS-KEY(...)`。
- **WoS**：普通关键词自动包装为 `TS=(...)`；若已含字段标签（`TS=`/`TI=`/`AU=`/`SO=` 等）则原样传递。布尔运算符（`AND`/`OR`/`NOT`）会被正确识别——顶层 `OR` 自动拆分为多次查询并合并结果（避免 WoS Starter API 的 400 错误）；`DO=(...)` 精确核验单篇原样传递。

## 请求行为（安全与健壮性）

- TLS 证书**默认校验**；仅当请求因 SSL 错误失败时，用宽松上下文自动重试一次（定向 fallback）。
- 对 **429 / 5xx** 与瞬时网络错误自动重试（最多 3 次，指数退避）。
- 请求携带 `User-Agent`（含 mailto），OpenAlex polite pool 与 Elsevier/Clarivate 均认可。

## 中文文献库接入说明

中文核心库（CNKI/万方/维普/百度学术/读秀等）**无公开 API**，不适合程序化接入，仅人工/机构入口；详见 [`references/chinese-sources.md`](references/chinese-sources.md)。

## 目录结构

```
thesis-retrieval/
├── SKILL.md              # skill 说明
├── manifest.yaml         # skill 元数据
├── README.md             # 本文档
├── INSTALL.md            # 安装指引（AI agent / 手动）
├── resources/
│   ├── config/
│   │   ├── config.env    # key 配置模板
│   │   └── config.local.env  # 本地 key 覆盖（可选，不入库）
│   ├── data/
│   │   └── journal_zones.json  # SCI 中科院分区映射表（期刊名→分区）
│   └── wos_shots/        # 截图 OCR 输出的图片目录（运行时生成）
├── scripts/
│   ├── thesis_retrieval.py # 核心检索脚本（纯 stdlib）
│   └── wos_snapshot.py   # WoS 截图+OCR 兜底脚本（可选依赖）
├── docs/
│   ├── Scopus_API申请与使用指南.md
│   ├── WoS_API申请与使用指南.md
│   ├── WoS截图OCR兜底说明.md
│   ├── SCI分区筛选说明.md
│   ├── 摘要筛选说明.md
│   └── 文献库配置说明.md
└── references/
    └── chinese-sources.md # 中文文献库接入说明（深参考）
```
