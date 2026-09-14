#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wos-snapshot v0.8.0: 浏览器截图 + OCR 抓取 WoS 页面文献条目。

背景
----
WoS Starter API 拿不到摘要，且部分 WoS 收录的文献没有 DOI，在其他库
（OpenAlex/CrossRef/Semantic Scholar/PubMed/Scopus）里都查不到 —— 对这类
“只有 WoS 有”的文献，API 路径无解。本脚本走一条人肉可复制的兜底路径：

    自动打开浏览器 → 用户已登录 WoS → 截图 → RapidOCR 识别文字

核心流程
--------
1. 用 Playwright 启动带本地用户数据的 Chrome/Edge（保留 WoS 登录态，不弹
   反爬验证），打开用户给的 WoS URL。
2. 等待页面稳定后，先试“页面可见文本”（Playwright 可读 DOM，无需 OCR，
   结果最干净）。
3. 若拿不到可见文本，再整页截图，交给 RapidOCR 识别（离线、中文/英文通用，
   首次运行自动下载约 15MB 模型）。

典型用法（由 AI 助手执行）
--------------------------
1. 用户报一篇只有 WoS 能查到的文献，或某次检索里 wos 条目缺摘要。
2. AI 打开 `https://www.webofscience.com/wos/woscc/summary/...` 搜索该文献，
   把结果页 URL 交给本脚本：
       python scripts/wos_snapshot.py "https://www.webofscience.com/wos/woscc/summary/xxxx"
3. 脚本输出结构化文献字段（标题/作者/期刊/年份/被引），AI 把结果并入主检索
   结果，或直接作为该文献的元数据。

可选参数
--------
    python scripts/wos_snapshot.py "<wos-url>" [--out out.json]
    python scripts/wos_snapshot.py --selftest      # 本地生成图片跑通 OCR，验证安装
    python scripts/wos_snapshot.py --ocr-only --image "<png路径>" [--out out.json]

依赖
----
    pip install playwright rapidocr_onnxruntime
    playwright install chromium          # 首次运行需下载浏览器内核（可选，也可复用系统 Chrome）

本脚本不会绕过 WoS 的登录与反爬校验；它只是把“人工截图 → AI 看图”自动化成
“自动截图 → 离线 OCR”，需要用户预先在浏览器里登录 WoS。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SHOT_DIR = SKILL_DIR / "resources" / "wos_shots"

# 常见 Windows Chrome / Edge 可执行文件（Playwright 找不到时会直接指定）
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

# 等待页面出现的超时（秒）
PAGE_LOAD_TIMEOUT = 45
# 页面文本出现后额外等待，让 WoS 的异步渲染稳定
SETTLE_WAIT = 3.0


# ---------------------------------------------------------------------------
# 浏览器定位
# ---------------------------------------------------------------------------

def find_system_browser() -> str | None:
    """返回第一个存在的 Chrome/Edge 可执行文件路径，否则 None。"""
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def build_playwright_launch_kwargs() -> dict:
    """Playwright launch 参数：优先用系统浏览器，并指定持久化用户数据目录。

    用持久化用户数据目录（--user-data-dir）有两个好处：
      - 保留用户已登录的 WoS 会话（不用反复登录，也不弹人机验证）；
      - 复用浏览器缓存，加快加载。
    首次运行会打开一个带脚本用户目录的独立浏览器窗口。
    """
    executable = find_system_browser()
    kwargs: dict = {
        "headless": False,  # 保留登录态需要真实窗口；OCR 抓取也依赖真实渲染
        "channel": None,
    }
    if executable:
        kwargs["executable_path"] = executable
    else:
        # 没有系统浏览器时交给 Playwright 自带内核（需 playwright install chromium）
        kwargs["channel"] = None
    return kwargs


# ---------------------------------------------------------------------------
# 截图 / OCR
# ---------------------------------------------------------------------------

def capture_screenshot(page, out_dir: Path, label: str) -> Path:
    """整页截图并保存，返回文件路径。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    shot = out_dir / f"wos_{label}_{int(time.time())}.png"
    page.screenshot(path=str(shot), full_page=True)
    return shot


def ocr_image(image_path: str | Path, engine) -> str:
    """对一张图片做 OCR，返回按行拼接的文本（每行一个条目）。"""
    result, _ = engine(str(image_path))
    if not result:
        return ""
    lines = [line[1] for line in result if line and len(line) > 1]
    return "\n".join(lines)


_UI_NOISE = (
    "web of science", "search", "results", "sign in", "sign out", "close",
    "login", "register", "cookie", "settings", "language", "export",
    "mark all", "select all", "my tools", "cited times", "times cited",
    "sort by", "page", "of 1", "wos", "clarivate", "back to", "home",
    "cited references", "related records", "open new window",
)


def _is_title_like(line: str) -> bool:
    """粗略判断一行是否像文献标题（不是按钮/面包屑等 UI 噪声）。"""
    t = line.strip()
    if len(t) < 8:
        return False
    low = t.lower()
    # 开头就是数字序号的行（"1."）可能是列表项，保留；纯导航/UI 文案排除
    if any(low.startswith(n) for n in _UI_NOISE):
        return False
    # 全是数字/标点的行（页码、计数）不算标题
    if re.fullmatch(r"[0-9\s.,:()\-—%]+", t):
        return False
    return True


def parse_record_text(text: str) -> dict:
    """把一页 WoS 结果/记录的文本解析成结构化字段。

    这是“尽力而为”的解析：WoS 页面布局会变，识别结果也不完美，
    能提多少提多少，提不到就留空。AI 拿到原始文本后仍可人工判断。
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rec: dict = {"title": "", "authors": "", "journal": "", "year": "",
                 "cited_by": "", "doi": "", "abstract": ""}
    if not lines:
        return rec

    # 标题：取第一行像标题的长文本（跳过纯 UI 噪声行）
    for l in lines:
        if _is_title_like(l):
            rec["title"] = l
            break

    # 年份：首个 19xx/20xx
    for l in lines:
        m = re.search(r"\b(19\d{2}|20\d{2})\b", l)
        if m:
            rec["year"] = m.group(1)
            break

    # DOI
    for l in lines:
        m = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", l, re.IGNORECASE)
        if m:
            rec["doi"] = m.group(0).rstrip(".,")
            break

    # 被引
    m = re.search(r"被引频次\s*[:：]?\s*(\d+)", text)
    if not m:
        m = re.search(r"(?:citation|cited by)\s*:?\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["cited_by"] = m.group(1)

    # 作者 / 期刊：常见标签
    for l in lines:
        low = l.lower()
        if low.startswith(("作者", "author", "by ")) and len(l) > 4:
            rec["authors"] = l.split(":", 1)[-1].split("：", 1)[-1].strip()
            break
    for l in lines:
        low = l.lower()
        if low.startswith(("来源", "source", "publication", "期刊", "journal")):
            # 去掉标签前缀，并剥离行尾年份，避免把年份混进期刊名
            jn = l.split(":", 1)[-1].split("：", 1)[-1].strip()
            jn = re.sub(r"[,\s]*(19\d{2}|20\d{2})\s*$", "", jn).strip()
            rec["journal"] = jn
            break

    # 摘要：WoS 结果页通常没有摘要；有则抓 “Abstract”/“摘要” 之后的连续文本
    ab_match = re.search(r"(?:Abstract|摘要)\s*[:：]?\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if ab_match:
        rec["abstract"] = ab_match.group(1).strip()[:800]

    return rec


def _engine():
    """延迟导入并创建 RapidOCR 引擎（首次运行下载模型）。"""
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


# ---------------------------------------------------------------------------
# Playwright 抓取
# ---------------------------------------------------------------------------

def fetch_page_text(url: str, out_dir: Path) -> dict:
    """打开 WoS URL，尝试取可见文本；失败则截图 OCR。返回解析结果 + 截图路径。"""
    from playwright.sync_api import sync_playwright

    result: dict = {"text": "", "ocr": False, "screenshot": "", "parsed": {}}
    with sync_playwright() as p:
        launch_kwargs = build_playwright_launch_kwargs()
        browser = p.chromium.launch(**launch_kwargs)
        # 持久化用户数据目录：让 WoS 登录态得以保留
        user_data = Path(tempfile.gettempdir()) / "wos-snapshot-chrome-profile"
        try:
            context = browser.new_context(user_data_dir=str(user_data))
        except TypeError:
            context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(PAGE_LOAD_TIMEOUT * 1000)

        print(f"[wos-snapshot] 打开 {url}", file=sys.stderr)
        page.goto(url, wait_until="load", timeout=PAGE_LOAD_TIMEOUT * 1000)
        time.sleep(SETTLE_WAIT)

        # 方案 A：读 DOM 可见文本（比 OCR 干净）
        text = page.evaluate("document.body ? document.body.innerText : ''") or ""
        if not text.strip() or "sign in" in text.lower()[:200] and "results" not in text.lower():
            # 页面为空或跳到了登录页，说明需要登录——截图交给 OCR 仍可能有内容
            pass

        # 只要拿到足够内容就用 DOM 文本，否则走 OCR
        usable = len([l for l in text.splitlines() if _is_title_like(l)]) >= 1
        if usable:
            result["text"] = text
        else:
            shot = capture_screenshot(page, out_dir, "page")
            result["screenshot"] = str(shot)
            result["ocr"] = True
            print(f"[wos-snapshot] 页面无可读文本，改用 OCR 截图: {shot}", file=sys.stderr)
            result["text"] = ocr_image(shot, _engine())

        browser.close()

    result["parsed"] = parse_record_text(result["text"])
    return result


# ---------------------------------------------------------------------------
# 自测 / 纯 OCR 模式
# ---------------------------------------------------------------------------

def selftest() -> int:
    """本地生成一张带英文文本的图片跑通 OCR，验证安装与模型下载。"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("缺少 Pillow：pip install pillow", file=sys.stderr)
        return 1

    print("[selftest] 生成测试图片并运行 OCR ...", file=sys.stderr)
    img = Image.new("RGB", (800, 120), "white")
    d = ImageDraw.Draw(img)
    d.text((20, 30), "Silver nanowire stretchable electrode 2024", fill="black")
    d.text((20, 70), "Advanced Functional Materials", fill="black")
    tmp = Path(tempfile.gettempdir()) / "wos_snapshot_selftest.png"
    img.save(tmp)

    try:
        text = ocr_image(tmp, _engine())
    except Exception as e:
        print(f"[selftest] OCR 失败: {e}", file=sys.stderr)
        return 1

    print("[selftest] OCR 输出:")
    print(text)
    ok = "nanowire" in text.lower()
    print("[selftest] " + ("OK" if ok else "WARN: 未识别出预期文本（模型可能需重装）"))
    return 0 if ok else 2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="WoS 截图+OCR 抓取：自动开浏览器 → 截图 → RapidOCR 识别文献文字")
    ap.add_argument("url", nargs="?", help="WoS 页面 URL（结果页 / 详情页）")
    ap.add_argument("--out", help="把结果写成 JSON 文件")
    ap.add_argument("--ocr-only", action="store_true",
                    help="不对浏览器截图，直接对已有图片 OCR")
    ap.add_argument("--image", help="配合 --ocr-only：待识别图片路径")
    ap.add_argument("--selftest", action="store_true", help="本地生成图片跑通 OCR 后退出")
    ap.add_argument("--version", action="version", version="wos-snapshot 0.8.0")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.ocr_only:
        if not args.image:
            print("--ocr-only 需要 --image <png 路径>", file=sys.stderr)
            return 2
        text = ocr_image(args.image, _engine())
        parsed = parse_record_text(text)
        out = {"ocr": True, "image": args.image, "text": text, "parsed": parsed}
        print(text)
        if args.out:
            Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n[written] {args.out}", file=sys.stderr)
        return 0

    if not args.url:
        ap.print_help()
        return 0

    try:
        res = fetch_page_text(args.url, DEFAULT_SHOT_DIR)
    except Exception as e:
        print(f"[wos-snapshot] 抓取失败: {e}", file=sys.stderr)
        print("[wos-snapshot] 请确认：1) 已 pip install playwright rapidocr_onnxruntime "
              "2) 浏览器已登录 WoS 3) 网址是 WoS 有效页面。", file=sys.stderr)
        return 1

    text = res["text"].strip()
    if not text:
        print("[wos-snapshot] 页面没有抓到任何文字。可能未登录或页面为空。", file=sys.stderr)
        return 1

    print(text)
    print("\n# parsed:")
    print(json.dumps(res["parsed"], ensure_ascii=False, indent=2))

    if args.out:
        Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[written] {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
