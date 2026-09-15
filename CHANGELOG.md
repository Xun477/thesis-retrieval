# Changelog

本 skill 的变更记录。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号采用 0.x 系列。

## [0.9.1] - 2026-09-15

### 修复（偏好持久化失效）

- **`--sources ... --save-sources` 不落盘**：显式传 `--sources` 时 `resolve_sources` 直接返回，从不调用 `save_sources`，
  导致 README 所述"覆盖保存默认文献库"无效。现改为显式 `--sources` 且带 `--save-sources` 时也写入 `resources/config/sources.env`。
- **`--filter always/never` 不持久化**：仅交互菜单里选 1/4 才保存，命令行显式传值不落盘。现改为显式 `--filter always/never` 同样写入 `preferences.env`。
- **`--zone N --zone-mode always` 不持久化**：仅交互菜单选"每次都这样"才保存，命令行显式传不落盘。现改为显式 `--zone-mode always` 同样写入 `preferences.env` 的 `ZONE_FILTER/ZONE_MIN`。
- **README**：快速开始补充 Windows 下中文乱码提示（`PYTHONIOENCODING=utf-8`）。

### 变更

- 版本号同步 0.9.1（脚本 / manifest / README / CHANGELOG）。

## [0.9.0] - 2026-09-14

### 新增（SCI 中科院分区筛选）

- **分区筛选核心**：`filter_by_zone()` 按中科院大类分区（1-4 区）过滤结果——只保留分区 ≤ 设定值的文献；未知期刊**保留**并标注 `分区=?`（不误删）。
- **本地分区映射表**：`resources/data/journal_zones.json`（期刊名→分区），`load_journal_zones()` 加载、`journal_zone()` 规范化匹配（精确 + 子串，如键 `advanced functional materials` 匹配 `Advanced Functional Materials (Weinheim)`）。
- **交互询问**：首次运行时询问「选分区（0 不限 / 1-4）+ 是否每次都这样？[y/N]」，支持"仅本次"与"以后都这样"两个选项。
- **偏好持久化**：`resources/config/preferences.env` 新增 `ZONE_FILTER=always/once` 与 `ZONE_MIN=1-4`；`save_zone_pref()` 保留原有 `FILTER_BY_ABSTRACT` 行（两设置共存）。
- **命令行**：`--zone 1-4`（分区下限）+ `--zone-mode always/once/off`（模式）。
- **输出标注**：文本结果显示 `分区=N`；`--out` JSON 新增 `dropped` 字段（被过滤的文献）。
- **docs/SCI分区筛选说明.md**：告诉用户分区数据源、首次交互、怎么改配置（改 preferences.env / 删除重选 / --zone 临时覆盖）、怎么补充期刊分区。

### 变更

- 版本号同步 0.9.0（脚本 / manifest / README / CHANGELOG）。

## [0.8.0] - 2026-09-11

### 新增（WoS 独有文献截图 + OCR 兜底）

- **`scripts/wos_snapshot.py`**：浏览器截图 + OCR 抓取 WoS 页面文献条目，解决"只有 WoS 收录、其他库查不到、也无 DOI"的文献无法程序化获取的问题。
  - Playwright 打开 WoS URL（自动查找系统 Chrome/Edge，持久化用户目录保留登录态，不绕过反爬）。
  - 优先读页面可见文本（DOM `innerText`，比 OCR 干净）；抓不到再整页截图交给 RapidOCR 离线识别（英文/中文通用，首次自动下载约 15MB 模型）。
  - 输出结构化字段：标题/作者/期刊/年份/DOI/被引（`parse_record_text` 尽力而为解析）。
  - `--selftest` 本地生成图片自测 OCR；`--ocr-only --image` 支持对已有截图单独识别；`--out` 写 JSON。
- **SKILL.md**：新增"WoS 独有文献兜底（截图+OCR）"执行路径。
- **docs/WoS截图OCR兜底说明.md**：调研结论 + 使用说明（借鉴 Zotero Connector `Web of Science.js` 翻译器与开源 WoS scraper 思路）。

### 变更

- 版本号同步 0.8.0（脚本 / manifest / README / CHANGELOG）。
- 依赖：核心检索仍零第三方依赖；截图 OCR 路径为可选依赖（`playwright` + `rapidocr_onnxruntime`）。

## [0.7.0] - 2026-09-11

### 新增（摘要提取 + 按摘要筛选）

- **六源摘要字段**：
  - OpenAlex：`abstract_inverted_index` 倒排索引重建原文。
  - CrossRef：`message.abstract` JATS 标签清洗（`<jats:p>` 转段落换行，去标签）。
  - Semantic Scholar：`abstract` 直接取（`fields=abstract`）。
  - Scopus / PubMed / WoS：默认不返回摘要（Scopus 需 COMPLETE view 多耗配额、PubMed 需额外 efetch、WoS API 本身无摘要），置 `None`。
- **跨源摘要兜底**：`fill_abstracts()` 按 DOI 把 OpenAlex/CrossRef/S2 的摘要补到无摘要的条目上。
- **摘要筛选偏好**：首次运行询问 `1 以后都是 / 2 仅本次 / 3 这次不用 / 4 以后都不用`，
  持久化到 `resources/config/preferences.env`（`FILTER_BY_ABSTRACT`）；`--filter` 临时覆盖。
- **`--abstracts`**：文本输出同时打印摘要（截断 300 字符）；`--out` JSON 始终含完整 `abstract` 字段。
- **AI 指令**：SKILL.md 增加"摘要筛选"章节——偏好启用时 AI 逐条读摘要标注 `[符合]/[不确定]/[排除]`。
- **docs/摘要筛选说明.md**：告诉用户后续如何修改筛选偏好（改 preferences.env / 删除重选 / --filter）。

### 变更

- 版本号同步 0.7.0（脚本 / manifest / README / CHANGELOG）。

## [0.6.0] - 2026-09-11

### 修复（WoS 布尔运算符 400）

- **修复根因**：`_to_wos_query` 之前把布尔运算符（`OR`/`AND`/`NOT`/`NEAR`/`SAME`）当普通词处理，
  导致 `silver OR gold` 变成非法的 `TS=(silver AND OR AND gold)`，WoS Starter API 返回 400。
  现在运算符被正确识别为运算符，不再当作词。
- **顶层 OR 自动拆分**：新增 `_split_or_terms`，裸词查询含顶层 `OR` 时自动拆成多次独立请求并合并结果
  （每片独立容错，单片失败打 warn 不崩溃；扇出上限 10 保护配额）。
  - 括号内/引号内的 OR 不拆（`TS=(a OR b)`、`"a OR b"`、`DO=(...)` 原样单次传递）。
- **`--sort cited/date`** 合并后全局排序正常。
- 验证：mock 全用例 + 真实 WoS API（`sodium ISFET OR ion-selective transistor` 修复前 400，修复后出结果；
  `silver nanowire AND gold`、`DO=(10.1016/j.cej.2021.132152)` 均正常）。

## [0.5.1] - 2026-09-10

### 改进（文档与 AI 指令）

- **WoS API 审核提醒**：`docs/WoS_API申请与使用指南.md` 顶部与申请步骤新增醒目提示——
  key 需人工审核、周期长（1-3 工作日+）；等待期间可先用其他文献库（openalex/crossref/
  semantic_scholar/pubmed/scopus），key 到位后再补 WoS。
- SKILL.md 凭据章节增加对应指令：WoS key 未就绪时检索优先用其他库，并告知用户 WoS 待补。

## [0.5.0] - 2026-09-10

### 新增（文献库持久化配置）

- **首次运行初始化**：未保存配置时弹菜单选择文献库，并询问"保存为默认还是仅本次"。
  - `y` → 保存到 `resources/config/sources.env`，以后每次直接用；
  - `N`/回车 → 仅本次生效。
- **持久化复用**：有保存配置时静默使用，不再弹菜单。
- **`--save-sources`**：命令行显式把本次选择写入默认配置。
- **`docs/文献库配置说明.md`**：说明用户如何换文献库（改 sources.env / 删除重初始化 / --sources 覆盖）。
- `resources/config/sources.env` 为本地用户配置，已加入 `.gitignore` 不随仓库提交。

### 变更

- 版本号同步 0.5.0（脚本 / manifest / README / CHANGELOG）。

## [0.4.1] - 2026-09-10

### 变更

- **config/ 移入 resources/config/**：key 配置文件路径更新（脚本 `CONFIG_FILE` 与文档引用同步），
  旧 `config/config.env` 不再读取。
- **新增 `references/troubleshooting.md`**：按故障主题整理 现象/原因/处理
  （key 缺失、429 限流、SSL、乱码、无结果、被引数缺失、安装等）。

## [0.4.0] - 2026-09-10

### 新增

- **docs/ 目录**：新增 `Scopus_API申请与使用指南.md` 与 `WoS_API申请与使用指南.md`，
  覆盖两个需 key 源的注册/申请步骤、Plan 对比、key 配置位置与常见用法。
- SKILL.md 凭据章节增加对 docs 指南的引用（AI 询问如何申请 key 时指向 docs）。

### 变更

- 版本号同步 0.4.0（脚本 / manifest / README / CHANGELOG）。

## [0.3.2] - 2026-09-09

### 改进（面向 AI 的指令优化）

- **SKILL.md 改为纯 AI 指令风格**：去掉面向人的解释性内容，只保留触发条件、执行步骤、
  命令约束、凭据、输出契约五块；运行时细节由 `--help` / `--list-sources` / `--check-keys` 自查。
- 版本号同步 0.3.2（manifest.yaml / README / 脚本）。

## [0.3.1] - 2026-09-09

### 改进（文档精简与自查）

- **精简 SKILL.md**：从约 167 行裁至约 40 行，只保留"何时用 / 怎么调"的调用协议；
  功能表、参数表、查询语法、请求行为等细节移入 README 或脚本自查。
- **新增 `--list-sources`**：运行时打印每个源的覆盖 / 凭据 / 限流 / 查询语法，
  取代原先硬编码在文档里的源信息表。
- 中文文献库接入说明移入 `references/chinese-sources.md` 深参考。

## [0.3.0] - 2026-09-09

新增三个免费无需 key 的检索源：**CrossRef**、**Semantic Scholar**、**PubMed**。

### 新增

- **CrossRef REST API**：免费、无需 key（建议填 `CROSSREF_MAILTO` 进 Polite Pool）。
  权威全球 DOI 元数据，含 `is-referenced-by-count` 被引数；支持 `--sort cited/date`。
- **Semantic Scholar**：免费、key 可选（`S2_API_KEY` 可提升共享限流）。
  含 `citationCount` 被引数；支持按引用排序。
- **PubMed（NCBI E-utilities）**：免费、key 可选（`NCBI_API_KEY` 将限流从 3 rps 提升到 10 rps）。
  生物医学主源，两段式 esearch + esummary。

### 改进

- `--check-keys` 现在显示全部 6 个源与 `mailto`。
- 交互多选菜单扩展为 6 个源，新源均免费免 key，默认选中且缺 key 标记逻辑不变。
- 去重优先级保持不变：openalex > scopus > wos > crossref > semantic_scholar > pubmed
  （权威源优先保留）。

### 说明

- Semantic Scholar 无 key 时使用共享限流，高峰期可能返回 429（脚本自动重试）。
- PubMed 不提供被引数，`cit=0` 不代表无人引（该源 `cited_by` 恒为 None）。

## [0.2.0] - 2026-09-09

聚合了两批改动（原分别标记为 1.1.0 与交互多选迭代），统一到 0.2.0。

### 新增

- **检索前交互式多选检索库**：不带 `--sources` 时，弹出编号多选菜单。
  - 支持编号多选（`2,3`）、名称多选（`scopus,wos`）、`all` 全选、回车默认全部可用库。
  - 缺 key 的库在菜单中标注"缺 key"，选中会被自动跳过，避免请求后静默失败。
  - 显式传 `--sources` 保持原非交互行为，脚本化 / CI 兼容。
- `--version` 参数，输出 `paper-research 0.2.0`。

### 改进（健壮性与安全）

- **TLS 证书默认校验**：原为绕开 pybliometrics 的 SSL bug 曾对**所有请求关闭证书校验**（中间人风险）。现改为默认校验证书，仅当某请求自身触发 SSL 错误时，用宽松上下文自动重试一次作定向 fallback。
- **请求重试**：对 429 / 5xx 及瞬时网络错误自动重试（最多 3 次，指数退避）。
- **User-Agent**：请求携带含 `mailto` 的 UA 头（OpenAlex polite pool、Elsevier、Clarivate 均认可）。
- **去重改进**：去重键由"标题前 80 字符"改为"完整规范化标题"（去空白、忽略大小写），避免误合并共享长前缀的不同论文。
- 抽出 `_cited_by()` helper，WoS 引用数解析更清晰且正确处理空 `citations`。
- 交互菜单排版改为空格对齐，Windows / UTF-8 终端显示更整齐。

## [0.1.1] - 2026-09-09

初始创建版（原标记 1.0.0）。

### 新增

- 统一多源学术检索 CLI：一次查询跨 **OpenAlex**（CrossRef/PubMed/arXiv 收录、免 key）、**Scopus**（Elsevier API，直接 HTTP 绕开 pybliometrics）、**Web of Science**（Clarivate WoS Starter API，自动包装 `TS=(...)` 语法）。
- 自动去重（源优先级 openalex > scopus > wos）、按相关度 / 被引 / 日期排序、JSON 导出（`--out`）。
- 多位置 API key 自动发现：环境变量 → `config/config.env` → `pybliometrics.cfg` → `lit-dl credentials.json`；单源缺 key 报错并跳过，其余源继续。
- `--check-keys` 检查 API key 配置。
