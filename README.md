# thesis-retrieval (v1.1.4)

统一多源学术文献检索 Skill。一次查询跨 **OpenAlex / CrossRef / Semantic Scholar / PubMed / Scopus / Web of Science** 六库检索，自动去重、按引用/日期排序、JSON 导出，支持 **SCI 中科院分区**与摘要贴合度筛选。核心零第三方依赖，四源免 key。

## 安装

- AI agent 安装：把 "按本仓库 INSTALL.md 安装 thesis-retrieval，完成后运行 `--version` / `--check-keys`" 发给 AI。
- 手动安装：详见 [INSTALL.md](INSTALL.md)（`git clone https://github.com/Xun477/thesis-retrieval ~/.claude/skills/thesis-retrieval`）。

首次运行须真人在终端完成三问式初始化（选库 → 摘要筛选 → SCI 分区），agent 环境可用 `python scripts/init_config.py` 弹窗引导。

## 快速开始

```bash
# 六库联合检索
python scripts/thesis_retrieval.py "silver nanowire" --sources openalex,crossref,semantic_scholar,pubmed,scopus,wos --sort cited --out results.json

# 用保存的默认库检索
python scripts/thesis_retrieval.py "silver nanowire"

# 首次初始化（须真实终端）
python scripts/thesis_retrieval.py "test"

# 体检
python scripts/thesis_retrieval.py --check-keys
```

> Windows 中文乱码时加 `PYTHONIOENCODING=utf-8` 前缀。

## 参数速览

| 参数 | 默认 | 说明 |
|------|------|------|
| `query` | — | 检索词 |
| `--sources` | 保存配置 | 参与检索的源，逗号分隔；首次运行交互初始化并保存 |
| `--save-sources` | — | 将本次选择保存为默认（`sources.env`） |
| `--source` | — | 只显示某源的结果（不影响检索） |
| `--limit` | 10 | 每源最大结果数（Scopus ≤25） |
| `--sort` | relevance | `relevance` / `cited` / `date` |
| `--out` | — | 写 JSON（含 abstract） |
| `--filter` | 保存偏好 | 摘要筛选：`always` / `once` / `no` / `never` |
| `--zone` / `--zone-mode` | 保存偏好 | SCI 分区下限 1-4；模式 `always` / `once` / `off` |
| `--check-keys` / `--list-sources` / `--version` | — | 体检 / 各源语法自查 / 版本 |

注意：`--sources` 控制查哪些库，`--source` 只过滤显示。

## 凭据

- 四源免 key：openalex / crossref / semantic_scholar / pubmed。
- scopus / wos 需 key（环境变量或 `resources/config/config.local.env`），缺 key 自动跳过；申请见 `docs/`。
- 可选提升限流：`OPENALEX_MAILTO` / `S2_API_KEY` / `NCBI_API_KEY`。

## WoS 独有文献兜底（截图 + OCR）

WoS 独有（无 DOI、其他库查不到）或需摘要/被引详情的文献，用浏览器截图 + OCR 兜底：

```bash
pip install playwright rapidocr_onnxruntime
python scripts/wos_snapshot.py "https://www.webofscience.com/wos/woscc/summary/xxxx" --out wos_snapshot.json
```

需浏览器已登录 WoS；脚本复用登录态，不绕过反爬。详见 [docs/WoS截图OCR兜底说明.md](docs/WoS截图OCR兜底说明.md)。

## 查询语法

- **OpenAlex / CrossRef / Semantic Scholar / PubMed**：普通关键词即可（PubMed 支持字段标签）。
- **Scopus**：`TITLE-ABS-KEY(...)` 高级语法。
- **WoS**：关键词自动包装为 `TS=(...)`；已有字段标签则原样传递；顶层 `OR` 自动拆分避免 400。

## 筛选与配置

- **摘要筛选**：AI 逐条读 abstract 标注 `[符合] / [不确定] / [排除]`；偏好存 `resources/config/preferences.env`（`FILTER_BY_ABSTRACT=`）。
- **SCI 分区**：本地映射表 `resources/data/journal_zones.json`（期刊名→分区 1-4），只保留分区 ≤ 设定值；未知期刊保留并标注 `分区=?`。分区表需按方向维护。
- 想改默认库：编辑 `sources.env` 的 `SOURCES=` 行，或删除该文件重新初始化。

详细说明见 `docs/`（文献库配置 / 摘要筛选 / SCI 分区 / API 申请）。

## 依赖与行为

- 核心检索仅 Python 标准库（3.9+）；WoS OCR 兜底需 playwright + rapidocr_onnxruntime。
- TLS 默认校验（仅 SSL 错误时定向 fallback 一次）；429/5xx 自动重试（最多 3 次，指数退避）。
- 中文核心库（CNKI 等）无公开 API，仅人工/机构入口，见 [references/chinese-sources.md](references/chinese-sources.md)。

## 目录结构

```
thesis-retrieval/
├── SKILL.md / manifest.yaml / README.md / INSTALL.md
├── scripts/   thesis_retrieval.py（核心）、init_config.py（初始化启动器）、wos_snapshot.py（OCR 兜底）
├── resources/ config/（key 模板、本地偏好）、data/journal_zones.json（分区表）
├── docs/      API 申请、分区/摘要筛选、OCR 兜底说明
└── references/ chinese-sources.md
```

## License

MIT，见 [LICENSE](LICENSE)。完整变更见 [CHANGELOG.md](CHANGELOG.md)。
