# 检索方案：OpenAlex / CrossRef / Semantic Scholar（简单三库）

> 这三个库语法简单，合并为一个文件说明。三者均**免 key** 直接可用。
> 与 `python scripts/thesis_retrieval.py --list-sources` 输出对应。

## OpenAlex

**库类型**：开放学术图谱，覆盖 CrossRef + PubMed + arXiv 收录。免 key，建议配 `OPENALEX_MAILTO` 进 polite pool 提升额度。

**检索方式**：普通关键词即 **title+abstract 全文搜索**（`filter=title_and_abstract.search`）。引号做精确短语。

**排序**（`--sort`）：
- `cited` → 按被引数 `cited_by_count:desc`
- `date` → 按发表日期 `publication_date:desc`
- `relevance`（默认）→ 相关度

**检索式写法**：
```
# 普通关键词（title+abstract 全文）
python scripts/thesis_retrieval.py "silver nanowire transparent electrode" --sources openalex

# 精确短语用引号
python scripts/thesis_retrieval.py "silver nanowire" --sources openalex

# 找被引最多的经典文献
python scripts/thesis_retrieval.py "silver nanowire" --sources openalex --sort cited
```

**注意**：OpenAlex 是「词在标题或摘要中出现」即命中，不做布尔语法解析；复杂布尔请靠同义词 OR 扩展 + 多个词自然 AND（同句分词默认全都要）。真正需要严格布尔 / 字段限定，用 Scopus 或 WoS（见各自文件）。

## CrossRef

**库类型**：全球 DOI 元数据（几乎全部期刊论文）。免 key，建议配 `CROSSREF_MAILTO` 进 Polite Pool。含被引数。

**检索方式**：`query.bibliographic` **书目检索**，接受普通关键词，对标题 / 作者 / 期刊 / DOI 综合匹配。

**排序**（`--sort`）：
- `cited` → 按被引数 `is-referenced-by-count` 降序
- `date` → 按出版日期降序
- `relevance`（默认）→ 相关度

**检索式写法**：
```
# 书目检索，按被引排序
python scripts/thesis_retrieval.py "silver nanowire" --sources crossref --sort cited

# 精确 DOI 核验单篇（检索词直接给 DOI 也可）
python scripts/thesis_retrieval.py "10.1016/j.cej.2021.132152" --sources crossref
```

**注意**：CrossRef 是「模糊匹配 + 相关度加权」，适合用标题片段或作者 + 关键词组合召回。严格按引用排序能快速定位领域经典。

## Semantic Scholar

**库类型**：跨学科（AI 领域强）。免 key；可选 `S2_API_KEY` 提升共享限流。含被引数。

**检索方式**：普通关键词即可（Graph API `paper/search`，`query` 参数）。

**排序**（`--sort`）：
- `cited` → 源级按被引数 `citationCount:desc` 排序
- `date` → 该源 API 请求**不加** date 排序参数；但合并后脚本会**全局按年份排序**（`sort_results`），所以 `--sort date` 对最终输出仍生效
- `relevance` → 源级不加排序参数，按 API 默认相关度；合并后不改序

**检索式写法**：
```
python scripts/thesis_retrieval.py "large language model" --sources semantic_scholar --sort cited
```

**注意**：无 key 时走共享限流，高峰期可能 429（脚本自动重试）。该源单次 API 请求本身不支持 date 排序（与 `--sort date` 的全局排序行为不同，见上）。

## 三库组合建议

三者免 key、语法简单，适合**快速初筛**。常规流程：
1. 先用 OpenAlex + CrossRef 联合检索（`--sources openalex,crossref`），按 `--sort cited` 找经典
2. 用 Semantic Scholar 补充 AI / 跨学科视角
3. 需要严格布尔、字段限定或 SCI 分区核验时，再上 Scopus / WoS（见对应文件）
