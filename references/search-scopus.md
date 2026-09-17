# 检索方案：Scopus

> Elsevier 全库。**必填 `SCOPUS_API_KEY`**（申请见 `docs/Scopus_API申请与使用指南.md`）。
> 接受 **Scopus 高级检索语法**，单独成文。
> 与 `python scripts/thesis_retrieval.py --list-sources` 输出对应。

## 机制

查询串**原样透传**为 Elsevier `query` 参数（`view=STANDARD`），所以 Scopus 高级检索语法直接生效。每源最大 **25 条**。

## 检索式写法

```
# 最常用：TITLE-ABS-KEY 限定标题+摘要+关键词
python scripts/thesis_retrieval.py "TITLE-ABS-KEY(silver nanowire AND transparent electrode)" --sources scopus

# 布尔组合 + 排除综述
python scripts/thesis_retrieval.py "TITLE-ABS-KEY(sodium AND ISFET) AND NOT (review)" --sources scopus

# 年份限定
python scripts/thesis_retrieval.py "TITLE-ABS-KEY(silver nanowire) AND PUBYEAR > 2020" --sources scopus
```

## 常用语法

| 语法 | 含义 | 示例 |
|------|------|------|
| `TITLE-ABS-KEY(...)` | 标题 + 摘要 + 关键词限定 | `TITLE-ABS-KEY(silver nanowire)` |
| `TITLE(...)` | 仅标题 | `TITLE(liquid metal)` |
| `AUTHKEY(...)` | 作者关键词 | `AUTHKEY(transparent electrode)` |
| `PUBYEAR` | 出版年份 | `PUBYEAR > 2020`、`PUBYEAR = 2021` |
| `AND` / `OR` / `AND NOT` | 布尔 | `A AND B AND NOT C` |
| `W/n` | 邻近算符（词距 n） | `silver W/3 nanowire` |
| `"..."` | 精确短语 | `"silver nanowire"` |
| `*` | 截词 | `conduct*` |

## 排序

Scopus 源级 API 请求**不加**排序参数（`ScopusSource.search` 不使用 sort 参数，以 API 默认相关度返回）；跨源合并后由脚本**全局按选定 `--sort` 排序**（`sort_results`，以脚本实现为准）。所以 `--sort cited/date` 对最终输出仍生效。

## 注意

- **默认无摘要**：Scopus 摘要需 `view=COMPLETE`（约 2 倍 API 配额），默认跳过以省免费额度；跨源时按 DOI 兜底补摘要。
- **限流 / 配额**：Elsevier API 按配额计费，检索 25 条上限是硬限制；429 脚本自动重试。
- **免费 / 机构 key**：可用个人 dev key（32 位 hex）或机构 InstToken（见申请指南）。
- 非 Elsevier 收录文献查不到，需配其他库。

## 适用场景

- 需要**严格字段限定 + 布尔**（比 OpenAlex 的模糊全文搜索更精准）
- Elsevier 系期刊覆盖（材料 / 化学 / 工程 / 医学）
- 与 WoS 做权威源交叉核验（Scopus ↔ WoS 互补）

## 与 WoS 互补

Scopus 和 WoS 覆盖面重叠但收录侧重不同，**两者都查能提高查全率**。需要 `DO=(...)` 精确核验单篇时用 WoS（见 `search-wos.md`），需要 `TITLE-ABS-KEY` 灵活字段限定时用 Scopus。
