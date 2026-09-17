# 检索方法论总纲（文献检索稳定流程）

> 本文件是 thesis-retrieval 检索方案的**通用方法论总纲**，不分库。
> 各文献库的**具体检索方案**见目录末尾「分库方案索引」。

面向 AI agent：给用户做**系统性的文献检索**（综述 / 开题 / 查新）时，按下面 5 个阶段走。核心思想：**检索不是一次性动作，而是可复现、可迭代的闭环。**

## 阶段 0：定义问题（检索前最重要）

**不要上来就搜**。先想清楚要解决什么问题，用 **PICO(S)** 框架拆解：

| 维度 | 含义 | 示例（银纳米线透明电极） |
|------|------|--------------------------|
| P（Population） | 研究对象 / 材料 / 场景 | 透明电极 |
| I（Intervention） | 干预 / 方法 / 技术 | 银纳米线 |
| C（Comparison） | 对照（没有可跳过） | — |
| O（Outcome） | 关注的结果 / 指标 | 导电性、透光率 |
| S（Study design，可选） | 研究类型限定 | — |

**产出**：一句清晰的研究问题 + 初步纳入 / 排除标准。拆解完，检索词自然浮现。

## 阶段 1：构建检索式（主题词 + 自由词 + 布尔逻辑）

单靠一个关键词搜不到好东西。**每个 PICO 维度列一组同义词（概念簇）**，再组合：

| 概念 | 同义词扩展 |
|------|-----------|
| 银纳米线 | silver nanowire, AgNW, silver nanowire network |
| 透明电极 | transparent electrode, TCO, transparent conductor |
| 导电性 | conductivity, sheet resistance |

**布尔逻辑组合规则：**
- **OR** 连接同一概念内的同义词 → 扩大查全率
- **AND** 连接不同概念 → 缩小范围、提高查准率
- **NOT** 排除无关类型（如 `NOT review`）

**通用技巧：**
- 字段限定：标题 `TI=` / `AB=` 摘要 / `[tiab]`（PubMed 风格）
- 截词符：`conduct*` 可匹配 conduct / conductivity / conductor
- 邻近算符：`NEAR` 限定词间距（各库写法不同，见分库文件）
- 短语：引号 `"silver nanowire"` 做精确匹配

**迭代原则**：第一版检索式几乎从不完美。跑一轮看结果，发现漏检 / 误检就调整同义词和布尔逻辑，**迭代 2-3 轮**，直到查全率（Recall）与查准率（Precision）平衡。

## 阶段 2：执行检索（多库 + 引文追踪 + 去重）

**选库策略**（不要只用一个库）：

| 场景 | 首选库 |
|------|--------|
| 生物医学 | PubMed / MEDLINE / Embase |
| 综合英文 | Web of Science / Scopus |
| 工程 / 计算机 | IEEE Xplore / ACM DL / DBLP |
| 中文 | CNKI / 万方 / 维普 |
| 预印本 | arXiv / bioRxiv |

**引文追踪（雪球法）—— 这步很多人漏掉，但能找回大量经典文献：**
- **反向追溯（backward snowballing）**：翻一篇**高被引综述**的参考文献，挖出奠基性论文
- **正向追踪（forward snowballing）**：看「谁引用了这篇种子文献」，追踪后续工作
- 工具：Connected Papers（可视化知识图谱）、ResearchRabbit、Litmaps

**跨库去重**：多库结果必然重复。基于 **DOI + 标题指纹**（去空白、忽略大小写）+ 作者序列 + 年份三重校验去重。

> thesis-retrieval 已自动完成「多库检索 + 去重 + 排序」，见下。

## 阶段 3：筛选（三步漏斗）

检索到大量文献后**不要全读**，漏斗式筛选：
1. **标题筛选**：先看标题，剔除明显无关的
2. **摘要筛选**：读摘要，按纳入 / 排除标准判断是否符合（配合本工具 `--filter` 摘要筛选与 `[符合]/[不确定]/[排除]` 标注）
3. **全文评估**：对通过的文献读全文，最终纳入

> 每步记录**剔除原因**（PRISMA 流程图的精髓），保证可复现。工具：Rayyan / Covidence 预筛选，Zotero 管理文献。

## 阶段 4：持续跟踪（让文献来找你）

检索不是一次性的，领域在更新，要持续跟进：
- **Google Scholar Alerts**：按关键词订阅，新文献自动推送
- **数据库提醒**：Web of Science / Scopus 保存检索式 + 邮件提醒
- **定期滚雪球**：每 1-2 个月，对最新综述的参考文献重新做一轮引文追踪
- **arXiv 每日摘要**：关注预印本最新进展

## 用 thesis-retrieval 落地阶段 1-2

```bash
# 六库联合检索，自动去重，按被引排序（找经典）
python scripts/thesis_retrieval.py "silver nanowire transparent electrode" --sources openalex,crossref,semantic_scholar,pubmed,scopus,wos --sort cited

# 只要 SCI 1-2 区文献
python scripts/thesis_retrieval.py "关键词" --zone 2 --zone-mode always

# 结果导出 JSON，方便 Zotero 管理
python scripts/thesis_retrieval.py "关键词" --out results.json
```

各库检索式写法见下方分库方案。运行时也可用 `python scripts/thesis_retrieval.py --list-sources` 自查每库语法。

## 分库方案索引

| 文件 | 适用库 | 语法复杂度 |
|------|--------|-----------|
| [`search-openalex-crossref-s2.md`](search-openalex-crossref-s2.md) | OpenAlex / CrossRef / Semantic Scholar | 简单（普通关键词） |
| [`search-pubmed.md`](search-pubmed.md) | PubMed | 特殊（字段标签 / MeSH） |
| [`search-scopus.md`](search-scopus.md) | Scopus | 高级（TITLE-ABS-KEY） |
| [`search-wos.md`](search-wos.md) | WoS | 复杂（TS= / 布尔 / OR 拆分） |
