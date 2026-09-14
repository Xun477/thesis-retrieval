# Scopus API(Elsevier)— 申请与使用指南

> 生成日期: 2026-08-25(由 WoS 指南同框架整理)
> 用途: 程序化检索 Scopus 文献 + 获取被引数,与 WoS/OpenAlex 交叉验证
> 前提: 机构已订阅 Scopus(确认后可用机构配额)
> 状态: 需自行配置 key(`~/.config/lit-dl/credentials.json` → `elsevier.api_key` 或环境变量);InstToken / pybliometrics.cfg 按需配置(见 §五)

---

## 一、为什么选 Scopus API

| 你的需求 | Scopus API 是否满足 |
|---|---|
| 按关键词检索文献 | ✅ Search API |
| 获取单篇完整元数据(摘要/作者/机构) | ✅ Abstract Retrieval API |
| 核实 DOI / 期刊 / 被引数 | ✅(Search + Citation Overview) |
| 与 WoS 检索结果交叉验证 | ✅ 两大库互补,减少漏检 |
| 免费 | ✅ 注册即得免费 key(研究用途) |

> 与 WoS Starter API 的差异: Scopus 覆盖面更广(含非 WoS 期刊)、检索式语法不同、被引口径不同(两库被引数不一致属正常,交叉验证时各自标注来源)。

---

## 二、核心 API 一览(均为 REST)

| API | 端点 | 用途 |
|---|---|---|
| **Scopus Search API** | `https://api.elsevier.com/content/search/scopus` | 检索文献(最常用) |
| **Abstract Retrieval API** | `https://api.elsevier.com/content/abstract/doi/{DOI}` | 单篇元数据+摘要 |
| Author Retrieval API | `https://api.elsevier.com/content/author/author_id/{id}` | 作者信息/发文统计 |
| Affiliation Retrieval API | `https://api.elsevier.com/content/affiliation/affiliation_id/{id}` | 机构信息 |
| Citation Overview API | `https://api.elsevier.com/content/citationoverview` | 引文概览(需授权) |
| Serial Title API | `https://api.elsevier.com/content/serial/title/issn/{issn}` | 期刊信息(分区核实) |

---

## 三、申请步骤(拿到 key)

1. **注册账号**
   - 打开 https://dev.elsevier.com/ → Register
   - **建议用机构邮箱注册**(机构资格/配额靠邮箱+机构识别)
   - 完成邮箱验证

2. **申请 API Key**
   - 登录后在 My API Key(或 Create API Key)处创建
   - 用途选 Research(学术研究免费)
   - 创建后得到一段 32 位 hex 格式的 **API Key**

3. **获取 Institutional Token(InstToken,可选但推荐)**
   - 用于标识机构身份,解锁机构订阅范围内的全文/授权数据
   - 获取方式: 联系图书馆或 Elsevier 客服/客户经理申请机构 token
   - 形式: `Elsevier-Insttoken-{机构名}-{随机串}`

4. **保存 key**
   - 写入 `~/.config/lit-dl/credentials.json` 的 `elsevier.api_key`(与 `wos.api_key` 平级):
     ```json
     {
       "elsevier": { "api_key": "你的_Scopus_key" },
       "wos": { "api_key": "你的_WoS_Starter_key" }
     }
     ```
   - 或设置环境变量 `ELS_API_KEY`(临时)

---

## 四、API 调用格式

### 认证(两个 header)
```
X-ELS-APIKey: 你的_API_Key          # 必填
X-ELS-Insttoken: 你的_InstToken      # 机构 token(有则加,解锁全文授权)
Accept: application/json
```

### 检索文献(核心)
```
GET https://api.elsevier.com/content/search/scopus?query=...
参数:
  query    = Scopus 检索式(语法见下),必填
  count    = 每页条数 1-25(默认 25)
  start    = 起始偏移(分页)
  date     = 年份范围,如 2021-PRESENT
  field    = 返回字段子集(省流量),如 eid,doi,title,coverDate,citedby-count
  sort     = 排序,如 -citedby-count(被引降序)
```

### 检索式语法(query 示例)
```
示例检索:
  TITLE-ABS-KEY(sodium AND ISFET)
  TITLE(sodium AND (ion-sensitive OR "field-effect")) AND PUBYEAR > 2020

限定 2021 后(两种写法):
  PUBYEAR > 2020
  date=2021-PRESENT

多字段组合:
  TITLE-ABS-KEY(sodium AND (ion-selective OR ionophore) AND (transistor OR FET))

排除:
  AND NOT (review)      # 排除综述(如需)
```

### 单篇详情
```
GET https://api.elsevier.com/content/abstract/doi/10.1016/j.snb.2023.134135
```

### 返回关键字段
- `entry[].dc:title`(标题)、`entry[].dc:identifier`(Scopus EID)、`entry[].prism:doi`
- `entry[].prism:coverDate`(出版日期)、`entry[].citedby-count`(**被引数**)
- `entry[].prism:publicationName`(期刊)、`entry[].author`(作者)

---

## 五、Python 调用(pybliometrics,可选)

常用包 `pybliometrics`,配置在 `~/.pybliometrics/pybliometrics.cfg`:

```ini
[Directories]
Config=.
Database=.

[Authentication]
APIKey = 你的_API_Key
InstToken = 你的_InstToken
```

```python
from pybliometrics.scopus import ScopusSearch
s = ScopusSearch('TITLE-ABS-KEY(sodium AND ISFET) AND PUBYEAR > 2020')
for e in s.results:
    print(e.doi, e.title[:60], e.citedby_count)
```

> 说明: 配置好上述文件后,即可用本项目的 `paper_research.py` 直接检索 Scopus。

---

## 六、配额与注意

- **免费 key 配额**: Search API 约 5,000 次/周(以门户实际显示为准);其他 API 配额各异
- 速率限制: 一般限 ~20 req/sec,批量请求需限速
- **被引数口径**: Scopus 被引 ≠ WoS 被引,属正常;交叉验证时标注数据来源
- 409/429 错误: 请求超配/速率超限,等待后重试
- key 用途: 学术研究免费;商用需付费授权

---

## 七、与项目已有工具链的关系

| 环节 | 工具 | 说明 |
|---|---|---|
| 检索筛选 | WoS Starter API | 见 `docs/WoS_API申请与使用指南.md` |
| 交叉核实 | Scopus API | 与 WoS 被引并列表述 |
| 开源兜底 | OpenAlex(免费无 key) | 无配额限制 |

---

## 附: 相关链接
- Elsevier 开发者门户: https://dev.elsevier.com/
- Scopus API 文档: https://dev.elsevier.com/documentation/ScopusSearchAPI.wadl
- API Key 管理: https://dev.elsevier.com/myapikeys.html
- pybliometrics 文档: https://pybliometrics.readthedocs.io/
