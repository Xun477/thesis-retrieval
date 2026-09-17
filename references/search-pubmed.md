# 检索方案：PubMed

> 生物医学库。免 key；可选 `NCBI_API_KEY` 将限流从 3 rps 提升到 10 rps。
> 语法特殊（字段标签 / MeSH / 布尔），单独成文。
> 与 `python scripts/thesis_retrieval.py --list-sources` 输出对应。

## 机制

脚本走 NCBI E-utilities **两段式**：
1. `esearch`：把 `term` 原样传给 NCBI 检索，返回 PMID 列表（`retmax` 上限 25 条）
2. `esummary`：按 PMID 拉取元数据（标题 / 作者 / 期刊 / 年份 / DOI）

**查询串是原样透传**给 NCBI 的 `term` 参数，所以 **PubMed 的字段标签和布尔语法全部直接生效**。

## 检索式写法

普通关键词、字段标签、布尔逻辑都支持：

```
# 普通关键词
python scripts/thesis_retrieval.py "sodium ISFET" --sources pubmed

# 字段限定：标题+摘要 [tiab]
python scripts/thesis_retrieval.py "silver nanowire[tiab]" --sources pubmed

# MeSH 主题词 [mh]
python scripts/thesis_retrieval.py "myocardial infarction[mh]" --sources pubmed

# 布尔组合 + 字段限定
python scripts/thesis_retrieval.py "transparent electrode[tiab] AND (silver nanowire OR AgNW)" --sources pubmed
```

## 常用字段标签

| 标签 | 含义 |
|------|------|
| `[tiab]` | 标题 + 摘要 |
| `[ti]` | 仅标题 |
| `[ab]` | 仅摘要 |
| `[mh]` | MeSH 主题词（受控词表，跨语言统一概念） |
| `[au]` | 作者 |
| `[dp]` | 发表日期（如 `2020:2026[dp]`） |
| `[pt]` | 文章类型（如 `review[pt]`） |

**MeSH 提示**：受控词表用「概念级」召回，能统一同义表达（如把 心梗 / MI 统一为 MeSH 词）；但它更新滞后（新兴术语早期无对应 MeSH 词），应**配合 `[tiab]` 自由词**使用——先 `[mh]` 保证查全，再加 `[tiab]` 自由词补新兴术语。

## 注意

- **无被引数**：PubMed 不暴露引用数，`cit=0` 不代表没人引（该源 `cited_by` 恒为 None）。要找被引数排序，用 OpenAlex / CrossRef / WoS / Scopus。
- **默认无摘要**：摘要需额外 efetch（默认跳过以省配额）。跨源检索时脚本会按 DOI 从 OpenAlex/CrossRef 兜底补摘要。
- **限流**：无 key 3 rps，有 `NCBI_API_KEY` 10 rps；429 脚本自动重试。
- 生物医学以外的主题，PubMed 覆盖率有限，可换综合库。

## 适用场景

- 生物医学 / 临床 / 生命科学文献
- 需要 MeSH 受控词表做**系统性查全**（配合 `[mh]` + `[tiab]` 双轨）
- 综述的医学主题部分

## 进阶：跨库核验

PubMed 的 PMID 与 DOI 并存，跨库检索后脚本按 DOI 去重；需要精确 DOI 核验单篇时，可与 CrossRef 或 WoS 的 `DO=(...)` 交叉验证。
