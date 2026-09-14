# WoS 独有文献兜底：截图 + OCR

> 适用场景：一篇文献**只有 Web of Science 能查到**（其他库查不到、也无 DOI），
> 或需要 WoS 的摘要/被引详情而 WoS Starter API 拿不到。
> 这类文献走 API 检索无解，本方案用「浏览器截图 + 文字识别」兜底。

## 为什么需要

| 问题 | 原因 |
|------|------|
| 其他库查不到 | 部分 WoS 收录文献无 DOI，OpenAlex/CrossRef/S2 无法定位；Scopus/PubMed 覆盖不全 |
| WoS API 拿不到摘要 | WoS Starter API（v1/v2）不返回 abstract 字段 |
| 人工操作太慢 | 每篇手动截图 → 贴给 AI 看，量大时不可行 |

## 方案原理

```
WoS 搜索结果页/详情页 URL
        │
        ▼
Playwright 打开浏览器（复用已登录会话，不绕过反爬）
        │
        ▼
读页面可见文本（DOM innerText，结果最干净）
   │  取不到（空页/登录页/图表）  │
   ▼                            ▼
用文本                       整页截图
                              │
                              ▼
                         RapidOCR 离线识别
                              │
                              ▼
                   标题/作者/期刊/年份/DOI/被引
```

- **文本优先，OCR 兜底**：WoS 是 SPA，页面加载后 DOM 里已有可见文本；只有
  读不到足够文本（登录页、纯图表、反爬页）才截图 OCR。
- **OCR 引擎选 RapidOCR**（`rapidocr_onnxruntime`）：完全离线、中英文通用、
  首次运行自动下载约 15MB 模型；不需要系统级 Tesseract，`pip install` 即用。

## 与现有方案的关系（调研结论）

1. **Zotero Connector 的 `Web of Science.js` 翻译器**（借鉴了思路，未直接复用其代码）：
   - 它通过**读取页面里的隐藏表单**（`records_form` / `output_form`）拿到记录 ID，
     再构造一个保存到 `saveToRef` 的 POST 请求，把选中记录以 ISI 格式导出并导入 Zotero。
   - 这是最"正规"的抓取路径，但依赖 WoS 旧版页面结构（`webofknowledge.com`），
     新版 `webofscience.com` 的 SPA 不再暴露这些表单，已失效。
2. **开源 WoS scraper 项目**（GitHub 上 `WOS-Citation-Scraper` 等）：
   - 多为**登录态 + 请求/解析**（requests + BeautifulSoup），依赖机构 IP 或账号。
   - 直接请求容易被反爬/风控，维护成本高；多数年久失修。
3. **WoS Starter API**（本项目已在用）：稳定但**无摘要、无无-DOI 文献**。
4. **截图 + OCR**（本方案）：不解析页面结构，对布局变化鲁棒；只要求"人能看到的
   文字能识别出来"。缺点是有 OCR 误差、需要真实浏览器会话。

> 结论：对"只有 WoS 有"的文献，截图 + OCR 是最稳妥的自动化兜底；
> 它把「人工截图 → AI 看图」自动化，不引入绕过反爬的风险。

## 使用步骤（AI 助手执行）

### 1. 首次准备

```bash
pip install playwright rapidocr_onnxruntime
# Playwright 优先复用系统 Chrome/Edge（脚本自动查找）；
# 无系统浏览器时：python -m playwright install chromium
```

自测 OCR 是否可用：

```bash
python scripts/wos_snapshot.py --selftest
# 输出示例：
# [selftest] OCR 输出:
# Silver nanowire stretchable electrode 2024
# Advanced Functional Materials
# [selftest] OK
```

### 2. 抓取一篇 WoS 页面

1. AI 用浏览器打开 WoS 搜索该文献，拿到结果页/详情页 URL。
2. 运行：

```bash
python scripts/wos_snapshot.py "https://www.webofscience.com/wos/woscc/summary/xxxx" --out wos_snapshot.json
```

3. 脚本自动打开浏览器 → 等页面稳定 → 读文本或截图 OCR → 打印页面文本与结构化字段。
4. 把识别出的字段并入检索结果，标注 `src=wos_snapshot`。

### 3. 对已有截图单独 OCR

```bash
python scripts/wos_snapshot.py --ocr-only --image 截图.png --out out.json
```

## 输出示例

```json
{
  "text": "Web of Science\nSearch\nResults: 3\n1. High-Performance ...\nAuthors: ...\nSource: Advanced Functional Materials, 2024\nCited by: 128\nDOI: 10.1002/adfm.202400123",
  "ocr": false,
  "screenshot": "",
  "parsed": {
    "title": "1. High-Performance Stretchable Electrodes Based on Silver Nanowires",
    "authors": "Zhang, Wei; Li, Ming",
    "journal": "Advanced Functional Materials",
    "year": "2024",
    "cited_by": "128",
    "doi": "10.1002/adfm.202400123",
    "abstract": ""
  }
}
```

> 注意：WoS 页面布局会变，`parsed` 是"尽力而为"解析。AI 应结合 `text`
> 原始文本判断，识别不准时人工修正字段，不强行套用。

## 失败排查

| 现象 | 处理 |
|------|------|
| 浏览器没打开 | 确认装了 `playwright`；系统无 Chrome/Edge 时先 `python -m playwright install chromium` |
| 打开后跳登录页 | 需先在浏览器登录 WoS；脚本用持久化用户目录，登录一次后复用 |
| OCR 输出乱码/空白 | 跑 `--selftest` 确认 OCR 可用；英文页面优先读 DOM 文本，OCR 只是兜底 |
| 页面是 WoS 新版 SPA 且无文本 | 截图会落到 `resources/wos_shots/`，可用 `--ocr-only --image` 重试 |
| 提示反爬/风控 | 人工截图即可，本脚本不提供绕过反爬的能力 |

## 依赖清单

- Python ≥ 3.9
- `playwright`（可选，仅截图路径）
- `rapidocr_onnxruntime`（可选，仅 OCR 路径）
- 系统 Chrome / Edge（可选，脚本自动查找）
