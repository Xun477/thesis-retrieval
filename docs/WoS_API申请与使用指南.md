# Web of Science Starter API — 申请与使用指南

> 生成日期: 2026-08-20
> 用途: 程序化检索 WoS 文献 + 获取被引次数,与 Scopus/OpenAlex 交叉验证
> 前提: 机构已订阅 Web of Science(确认后可用机构配额)

> ⚠️ **重要提醒：WoS API key 需要人工审核，周期较长（通常 1-3 个工作日，机构管理员审批时可能更久）。**
> 在 key 下发之前，**可先用其他文献库**（OpenAlex / CrossRef / Semantic Scholar / PubMed 免费免 key 即用；Scopus 也可先用）完成检索与交叉验证，WoS 后续补上即可。

---

## 一、为什么选 Starter API

| 你的需求 | Starter API 是否满足 |
|---|---|
| 按关键词检索文献 | ✅ `GET /documents?q=...` |
| 获取每篇被引次数 | ✅(Institutional Plan) |
| 核实 DOI / 期刊 / 作者 | ✅ |
| 免费 | ✅ 三个 Plan 均免费 |
| 申请门槛 | 低(Institutional Member 需机构订阅) |

> 已被 Lite API 取代;Expanded API 功能更强但申请门槛高,一般检索用 Starter 足够。

---

## 二、三个 Plan 对比(全部免费)

| Plan | 每秒/每日 | 被引次数 | 申请门槛 |
|---|---|---|---|
| Free Trial Plan | 1 / 50 | ❌ 不含 | 所有人可开 |
| **Free Institutional Member Plan**(推荐) | 5 / 5,000 | ✅ 含 | **需机构订阅 WoS** |
| Free Institutional Integration Plan | 5 / 20,000 | ✅ 含 | 需机构管理员审批 |

**选择**: 申请 **Free Institutional Member Plan**,5,000 次/天 + 含被引,足够一般研究使用。

---

## 三、申请步骤(拿到 key)

1. **注册账号**
   - 打开 https://developer.clarivate.com/ → Sign Up
   - **建议用机构邮箱注册**(机构资格靠邮箱识别)
   - 完成邮箱验证

2. **创建应用(Application)**
   - 登录后进入 My Apps → Create App
   - 应用名称随意填,如 `Paper Search`
   - 创建后进入应用详情页

3. **订阅 Starter API**
   - 在应用里点 Add API / Subscribe
   - 选择 **Web of Science Starter API**
   - 选择 **Free Institutional Member Plan**
   - 同意 Terms of Use

4. **获取 API Key**
   - 订阅后在应用详情页(或 API 的 Keys 标签页)查看
   - 得到 64 位 hex 格式的 **API Key**
   - **需人工审核**: 提交后等待 Clarivate 管理员审批,通常 **1-3 个工作日**,高峰期可能更久
   - **等待期间**: 不要卡在 WoS 上——先用 OpenAlex / CrossRef / Semantic Scholar / PubMed / Scopus 完成检索,key 下来后再补 WoS 结果

5. **保存 key**(两种方式)
   - **方式一**: 写入 `~/.config/lit-dl/credentials.json` 的 `wos.api_key`(与 Elsevier key 平级)
   - **方式二(手动)**: 编辑 `~/.config/lit-dl/credentials.json`,加入:
     ```json
     {
       "elsevier": { "api_key": "你的_Scopus_key" },
       "wos": { "api_key": "你的_WoS_Starter_key" }
     }
     ```
   - 或设置环境变量 `WOS_API_KEY`(临时,重启失效)

---

## 四、API 调用格式

### 认证
所有请求带 header:
```
X-ApiKey: 你的_API_Key
```

### 检索文档(核心)
```
GET https://api.clarivate.com/apis/wos-starter/v1/documents
参数:
  q          = WoS 高级检索式,必填
  db         = WOS(Web of Science Core Collection,默认)
  limit      = 每页条数 1-50(默认 50)
  page       = 页码
  sortField  = 排序,如 'PY+D'(年份降序)
  publishTimeSpan = 出版时间范围,如 '2021-01-01+2026-12-31'
```

### 检索式示例(q 参数)
```
示例检索:
  TI=(sodium AND ISFET) OR AB=(sodium AND ion-sensitive field-effect)

限定 2021 后:
  TI=(sodium AND ISFET) AND PY=2021-2026

多离子:
  TI=(sodium AND (ion-selective OR ionophore) AND (transistor OR FET))
```

### 获取单篇详情
```
GET https://api.clarivate.com/apis/wos-starter/v1/documents/{UID}
```

### 返回字段(含)
UID、Title、DOI、Times Cited、Source、Authors、Author Keywords、Publication Date 等

---

## 五、配额注意
- **Free Trial(50次/天)** 不含被引次数——验证 key 是否生效可先用它
- **Institutional Member(5000次/天)** 才返回 Times Cited
- 若申请后只有 Trial,可联系机构图书馆确认机构资格关联

---

## 六、拿到 key 后
1. 把 key 写入本项目的 `resources/config/config.env`(或环境变量)
2. 直接运行:
   ```bash
   python scripts/thesis_retrieval.py "sodium ion sensor" --sources wos --sort cited
   ```
   WoS 条目即返回标题/期刊/被引等字段。

---

## 附: 相关链接
- 门户: https://developer.clarivate.com/
- Starter API 产品页: https://developer.clarivate.com/apis/wos-starter
- Swagger 文档: https://api.clarivate.com/swagger-ui/?url=https://developer.clarivate.com/apis/wos-starter/swagger
- WoS 帮助(检索式语法): https://webofscience.help.clarivate.com/en-us/Content/advanced-search.html
- 官方 GitHub 示例: https://github.com/clarivate?q=wosstarter
