# 检索方案：Web of Science（WoS）

> Clarivate 核心合集。**必填 `WOS_API_KEY`**（申请见 `docs/WoS_API申请与使用指南.md`，人工审核 1-3 工作日+）。
> 语法最复杂（字段标签 / 布尔 / OR 拆分），单独成文。
> 与 `python scripts/thesis_retrieval.py --list-sources` 输出对应。

## 机制

WoS Starter API 的 `q` 参数**要求显式字段标签**。脚本逻辑：
1. 查询串已含字段标签（`TS=`/`TI=`/`AB=`/`AU=`/`SO=`/`PY=`/`DO=` 等）→ **原样透传**
2. 否则**自动包装为 `TS=(...)`**（主题检索），裸词之间用 `AND` 连接
3. 布尔运算符（`OR`/`AND`/`NOT`/`NEAR`/`SAME`）被识别为**运算符**而非普通词（避免 `TS=(silver AND AND AND gold)` 触发 HTTP 400）
4. 查询含**顶层 `OR`** → 自动拆分成多次请求并合并结果（`_split_or_terms`，扇出上限 10，单片失败打 warn 不崩溃）

每源最大 **50 条**。

## 检索式写法

```
# 自动包装为 TS=(...)
python scripts/thesis_retrieval.py "silver nanowire" --sources wos
# → q=TS=(silver AND nanowire)

# 已含字段标签则原样传递
python scripts/thesis_retrieval.py "TI=(sodium AND ISFET) OR AB=(ion-selective transistor)" --sources wos

# 布尔组合（自动处理）
python scripts/thesis_retrieval.py "silver AND gold" --sources wos
# → TS=(silver AND gold)，不会 400

# 顶层 OR 自动拆分
python scripts/thesis_retrieval.py "sodium ISFET OR ion-selective transistor" --sources wos
# → 拆成 TS=(sodium AND ISFET) + TS=(ion-selective AND transistor) 两次请求，合并结果

# 精确核验单篇
python scripts/thesis_retrieval.py "DO=(10.1016/j.cej.2021.132152)" --sources wos
```

## 常用字段标签

| 标签 | 含义 |
|------|------|
| `TS=(...)` | 主题（标题 + 摘要 + 关键词） |
| `TI=(...)` | 标题 |
| `AB=(...)` | 摘要 |
| `AU=(...)` | 作者 |
| `SO=(...)` | 来源出版物（期刊） |
| `PY=...` | 出版年（如 `PY=2021-2026`） |
| `DO=(...)` | DOI 精确匹配（核验单篇用） |

## 布尔与邻近运算符

`AND` / `OR` / `NOT` / `NEAR` / `SAME` 均被识别为运算符。**括号内或引号内的 OR 不拆分**（如 `TS=(a OR b)` 原样单次传递），仅顶层裸 OR 才拆分。

## 注意

- **无摘要**：WoS Starter API 不返回摘要（v1/v2 均无）；跨源时按 DOI 从 OpenAlex/CrossRef 兜底补摘要。
- **被引数**：从 `citations` 字段解析，`cit=0` 需结合跨源判断。
- **key 审核周期长**：等待期间可先用其他 5 库，key 到位后再补 WoS。
- **WoS 独有文献**（无 DOI、其他库查不到）：API 路径无解，用截图+OCR 兜底——见 `docs/WoS截图OCR兜底说明.md` 和 `scripts/wos_snapshot.py`。

## 适用场景

- 需要 **TS= 主题检索**的权威综合库
- **精确 DOI 核验**单篇（`DO=(...)`）
- 与 Scopus 互补提高综合查全率
- WoS 核心合集收录的经典文献（高被引排序权威）

## 已知边界

- 顶层 OR 拆分的扇出上限 10：超过 10 个顶层 OR 分支时，脚本**放弃拆分、按原样单次请求**（打 warn 提示，见 `scripts/thesis_retrieval.py:_split_or_terms`），此时查询以 `TS=(...)` 原样传给 WoS。需要更宽的布尔检索建议分批查询。
- 字段标签需用**大写**（脚本按 `re.IGNORECASE` 识别但建议规范大写）。
