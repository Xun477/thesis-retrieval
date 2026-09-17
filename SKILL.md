---
name: thesis-retrieval
description: >-
  用户要查文献/找论文/跨库检索/查引用数/论文查新/写文献综述的检索部分时使用本 skill。
  一次查询跨 OpenAlex、CrossRef、Semantic Scholar、PubMed、Scopus、Web of Science 六大库，
  自动去重、按引用/日期排序、支持 JSON 导出；可按 SCI 中科院分区（1-4 区）和摘要筛选；
  WoS 独有文献可用浏览器截图+OCR 兜底抓取。无论用户说"帮我搜一下关于X的论文"、
  "查查X方向的文献"、"哪些论文被引最多"、"找几篇X的paper/文献"、"查这个期刊是几区"，都应用本 skill。
  英文触发: multi-source paper search, cross-database literature retrieval,
  find highly-cited papers, arXiv/PubMed/Crossref/SemanticScholar/Scopus/WoS search,
  journal quartile filter.
license: MIT
compatibility: Python 3.9+; WoS OCR 兜底需 playwright + rapidocr_onnxruntime
---

# thesis-retrieval — 统一多源学术检索

## 触发条件
- 用户请求查文献、找论文、跨库检索、查引用数、论文查新、文献综述检索部分。

## 不触发
- 单篇深度解读 → `nature-paper-card`；引文验证/MeSH → `nature-academic-search`；PDF/图注 → 专门 skill。

## 执行步骤
0. **首次运行（无 `resources/config/sources.env`）须由真人在真实终端完成初始化**（三问式：选库 → 摘要筛选 → SCI 分区），走完后配置落盘。AI agent 若检测到脚本输出"需要人工初始化"，应停下并请用户在终端跑一次 `python scripts/thesis_retrieval.py "test"`，**不要**尝试绕过或用 `--sources` 静默代替初始化。
1. 运行 `python scripts/thesis_retrieval.py "<query>"`。
   - 无保存配置（首次）：交互选择文献库，选完自动保存到 `resources/config/sources.env`（须真人，见上）。
   - 有保存配置：直接用保存的库，不弹菜单。
2. 需要临时指定库：显式传 `--sources`（覆盖保存配置，仅本次）。
3. 结果按需加 `--sort cited|date`、`--out file.json`。

## 检索方案（按需读取，不内联）
- 系统检索方法论（PICO 拆解 → 检索式构建 → 多库 → 引文追踪 → 筛选 → 跟踪）：`references/search-methodology.md`。
- 各库检索方案（语法不同，按库读取）：OpenAlex/CrossRef/S2 → `references/search-openalex-crossref-s2.md`；PubMed → `references/search-pubmed.md`；Scopus → `references/search-scopus.md`；WoS → `references/search-wos.md`。

## 命令约束
- `--sources` 控制检索哪些库（临时）；`--save-sources` 把选择写入 `resources/config/sources.env` 作为默认；`--source` 只过滤显示。
- 前四源免费免 key：openalex/crossref/semantic_scholar/pubmed。scopus/wos 需 key，缺 key 自动跳过。
- 单源失败不影响其余源（报错到 stderr）。
- 其他参数与各源语法：`--help` / `--list-sources` / `--check-keys` 运行时自取。

## 文献库配置（用户如何换库）
- 用户想改默认文献库：编辑 `resources/config/sources.env` 的 `SOURCES=` 行，或删除该文件重新初始化，或用 `--sources ... --save-sources` 覆盖。
- 详见 `docs/文献库配置说明.md`。

## 凭据
- 环境变量 → `resources/config/config.env` → 其他。详情 `--check-keys`。
- 申请 scopus/wos key：见 `docs/Scopus_API申请与使用指南.md`、`docs/WoS_API申请与使用指南.md`。
- **WoS key 需人工审核、周期长（1-3 工作日+）**：key 未就绪时，检索优先用其他库（openalex/crossref/semantic_scholar/pubmed/scopus），并向用户说明 WoS 待 key 到位后补查。

## 输出契约
- 文本一行一篇：`[年份] 标题 | 期刊 | src=源 | cit=引用数 | DOI`；`--abstracts` 时每篇追加摘要段。
- `--out` 写 `{query, results, errors}`，字段 `title/authors/year/doi/journal/cited_by/source/abstract`。

## 摘要筛选（AI 必须执行）
- 摘要偏好持久化在 `resources/config/preferences.env`（`FILTER_BY_ABSTRACT=always/once/no/never`），首次运行询问，`--filter` 可临时覆盖。用户改偏好见 `docs/摘要筛选说明.md`。
- 当偏好为 `always` 或 `once` 时，检索后 **AI 必须读每条结果的 abstract，逐条判定是否贴合用户需求**，输出时标注：
  - `[符合]` 摘要明确支持用户需求的
  - `[不确定]` 摘要相关但不明确的
  - `[排除]` 摘要明显不符合的（并给出一句理由）
- 优先用 `--out` JSON（abstract 字段完整）做筛选，避免文本截断。
- 摘要缺失（PubMed/WoS/Scopus 默认不返回）：跨源已尽力兜底，缺失时按标题+期刊判断，标注"无摘要"。

## SCI 分区筛选（中科院分区）
- 分区偏好持久化在 `resources/config/preferences.env`（`ZONE_FILTER=always/once` + `ZONE_MIN=1-4`），首次运行询问，`--zone` / `--zone-mode` 临时覆盖。用户改偏好见 `docs/SCI分区筛选说明.md`。
- 分区数据来自本地映射表 `resources/data/journal_zones.json`（期刊名→分区，1 区最高）。未知期刊**保留**并标注 `分区=?`。
- 当偏好为 `always` 或本次选择了分区时，检索后按 `ZONE_MIN` 过滤：只保留分区 ≤ ZONE_MIN 的文献，高于的被放入 `--out` JSON 的 `dropped` 字段，并在文本输出标注 `分区=N`。
- 分区表需用户按研究方向维护（从 LetPub 查中科院大类分区填入）；未收录期刊显示 `分区=?` 不误删。

## WoS 独有文献兜底（截图+OCR）
- 当某文献只有 WoS 能查到（其他库查不到、也无 DOI），或需要 WoS 摘要/被引详情而 API 拿不到时：
  1. AI 用浏览器打开 WoS 搜索该文献，把结果页/详情页 URL 交给 `python scripts/wos_snapshot.py "<url>"`。
  2. 脚本自动打开浏览器 → 读页面文本（或截图）→ RapidOCR 识别 → 输出结构化字段（标题/作者/期刊/年份/DOI/被引）。
  3. 把识别结果并入检索结果，作为该文献的元数据；标注来源 `src=wos_snapshot`。
- 前置依赖（首次）：`pip install playwright rapidocr_onnxruntime`；`--selftest` 可自测 OCR。
- 需要用户在浏览器里**预先登录 WoS**（脚本复用登录态，不绕过反爬）。抓不到时检查登录与 URL 有效性，并如实告知用户。

## 中文文献
- 中文核心库无 API 可接入；需要中文文献用 OpenAlex 或 dataPro-search MCP；全文需人工/机构入口。详见 `references/chinese-sources.md`。

## 故障
- 遇到错误/异常输出，先查 `references/troubleshooting.md` 对应条目再处理。
