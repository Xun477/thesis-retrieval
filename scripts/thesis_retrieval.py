#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
thesis-retrieval v1.1.1: Unified multi-source academic paper search.

Interactive source selection:
    Running without --sources opens a numbered multi-select menu before
    searching so the user picks which libraries to query each time:
        [1] openalex [2] crossref [3] semantic_scholar [4] pubmed
        [5] scopus  [6] wos   ->  type "2,3" / "crossref,pubmed" /
    "all" for everything, or just Enter for every source with a configured key.
    Sources without a key are listed but skipped. Passing --sources stays
    fully non-interactive for scripting.

Combines six search channels into one CLI (v0.3.0 added crossref /
semantic_scholar / pubmed; v0.7.0 adds --list-sources):
  1. OpenAlex        (free; covers CrossRef + PubMed + arXiv deposits)  [default]
  2. Crossref        (free; doidata of papers via CrossRef REST)
  3. Semantic Scholar(free; citation-aware, AI-heavy coverage)
  4. PubMed          (free; biomedicine via NCBI E-utilities)
  5. Scopus          (Elsevier API via direct HTTP, bypasses pybliometrics SSL bug)
  6. WoS             (Clarivate WoS Starter API)

HTTP client behaviour:
  - TLS certificates are VERIFIED by default. Only if a request fails with an
    SSL error is it retried once with an unverified context (targeted fallback
    for broken local TLS, instead of globally disabling verification).
  - Retries 429 / 5xx / transient errors with exponential backoff (max 3).
  - Sends a User-Agent header containing the configured mailto.

Usage:
    python thesis_retrieval.py "silver nanowire"                    # interactive source pick
    python thesis_retrieval.py "silver nanowire liquid metal electrode" --sources openalex,crossref,semantic_scholar,pubmed,scopus,wos --limit 10 --sort cited --out results.json
    python thesis_retrieval.py "silver nanowire" --source wos --limit 5
    python thesis_retrieval.py --check-keys          # verify all API keys
    python thesis_retrieval.py --version             # show version (1.1.1)
    python thesis_retrieval.py --list-sources        # show sources / credentials / syntax

Environment / config:
    Keys are read (in order) from:
      1. env vars:  SCOPUS_API_KEY, WOS_API_KEY, OPENALEX_MAILTO
      2. resources/config/config.env in this skill dir (KEY=value lines)
      3. pybliometrics.cfg (Scopus APIKey)
      4. lit-dl credentials.json (elsevier.api_key / wos.api_key)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

ALL_SOURCES = ["openalex", "crossref", "semantic_scholar", "pubmed", "scopus", "wos"]

SOURCE_HINTS = {
    "openalex": "免费 · 无需 key · 覆盖 CrossRef/PubMed/arXiv",
    "crossref": "免费 · 建议 mailto · 全球 DOI 元数据",
    "semantic_scholar": "免费 · key 可选 · 含被引数",
    "pubmed": "免费 · key 可选 · 生物医学库",
    "scopus": "Elsevier 全库 · 需 SCOPUS_API_KEY",
    "wos": "Clarivate 核心合集 · 需 WOS_API_KEY",
}

# ---------------------------------------------------------------------------
# Config discovery
# ---------------------------------------------------------------------------

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = SKILL_DIR / "resources" / "config" / "config.env"
SOURCES_FILE = SKILL_DIR / "resources" / "config" / "sources.env"
PREFERENCES_FILE = SKILL_DIR / "resources" / "config" / "preferences.env"
JOURNAL_ZONES_FILE = SKILL_DIR / "resources" / "data" / "journal_zones.json"
PYBIO_CFG = Path.home() / ".config" / "pybliometrics.cfg"
LITDL_CRED = Path.home() / ".config" / "lit-dl" / "credentials.json"


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=value config file."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    except Exception:
        pass
    return out


def load_saved_sources() -> list[str]:
    """Load previously saved source selection from resources/config/sources.env.

    The file stores one source per line (or a comma list). Returns [] if unset.
    """
    if not SOURCES_FILE.exists():
        return []
    raw = _read_env_file(SOURCES_FILE).get("SOURCES", "")
    if not raw:
        return []
    return [s.strip().lower() for s in re.split(r"[, ]+", raw) if s.strip().lower() in set(ALL_SOURCES)]


def save_sources(sources: list[str]) -> None:
    """Persist the chosen source list to resources/config/sources.env."""
    try:
        SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        body = "# thesis-retrieval 持久化文献库选择（由首次初始化或 --save-sources 写入）\n"
        body += "# 想换文献库：改下面这行，或删除本文件后重新初始化，或运行时用 --sources 覆盖。\n"
        body += "SOURCES=" + ",".join(sources) + "\n"
        SOURCES_FILE.write_text(body, encoding="utf-8")
    except OSError as e:
        print(f"[warn] 无法保存文献库配置: {e}", file=sys.stderr)


def load_filter_pref() -> str | None:
    """Load saved abstract-filter preference from resources/config/preferences.env.

    Returns one of always|once|no|never, or None if unset.
    """
    if not PREFERENCES_FILE.exists():
        return None
    v = _read_env_file(PREFERENCES_FILE).get("FILTER_BY_ABSTRACT", "").strip().lower()
    return v if v in ("always", "once", "no", "never") else None


def save_filter_pref(value: str) -> None:
    """Persist the abstract-filter preference to resources/config/preferences.env.

    Preserves the existing ZONE_FILTER/ZONE_MIN lines so the two settings
    coexist in the same file (symmetric with save_zone_pref).
    """
    try:
        PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        cur = _read_env_file(PREFERENCES_FILE)
        zone_mode = cur.get("ZONE_FILTER", "")
        zone_min = cur.get("ZONE_MIN", "")
        body = ("# thesis-retrieval 摘要筛选偏好（FILTER_BY_ABSTRACT）\n"
                "#   always = 以后每次都按摘要筛选（推荐）\n"
                "#   once   = 仅本次筛选\n"
                "#   no     = 本次不筛选\n"
                "#   never  = 以后都不用，也不再询问\n"
                "# 想修改：改下面这行，或删除本文件后重新初始化，或用 --filter 临时覆盖。\n"
                f"FILTER_BY_ABSTRACT={value}\n")
        if zone_mode and zone_min:
            body += f"ZONE_FILTER={zone_mode}\n"
            body += f"ZONE_MIN={zone_min}\n"
        PREFERENCES_FILE.write_text(body, encoding="utf-8")
    except OSError as e:
        print(f"[warn] 无法保存筛选偏好: {e}", file=sys.stderr)


def load_zone_pref() -> tuple[str | None, int | None]:
    """Load saved SCI-zone preference from preferences.env.

    Returns (mode, min_zone) where mode is 'always'|'once'|None and
    min_zone is 1-4 or None (disabled). Empty when unset.
    """
    if not PREFERENCES_FILE.exists():
        return None, None
    prefs = _read_env_file(PREFERENCES_FILE)
    mode = prefs.get("ZONE_FILTER", "").strip().lower()
    mode = mode if mode in ("always", "once") else None
    try:
        min_zone = int(prefs.get("ZONE_MIN", "0"))
        min_zone = min_zone if 1 <= min_zone <= 4 else None
    except ValueError:
        min_zone = None
    return mode, min_zone


def save_zone_pref(mode: str, min_zone: int) -> None:
    """Persist the SCI-zone filter preference to preferences.env.

    Preserves the existing FILTER_BY_ABSTRACT line so the two settings
    coexist in the same file.
    """
    try:
        PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        cur = _read_env_file(PREFERENCES_FILE)
        existing = cur.get("FILTER_BY_ABSTRACT", "")
        lines = [
            "# thesis-retrieval 分区筛选偏好（中科院分区）\n",
            "#   ZONE_FILTER = always=以后每次都按分区筛  once=仅本次  （缺省=不筛）\n",
            "#   ZONE_MIN    = 1|2|3|4  保留「分区 <= 该值」的文献（1 区最高）\n",
            "# 想修改：改下面两行，或删除本文件后重新初始化。\n",
            f"ZONE_FILTER={mode}\n",
            f"ZONE_MIN={min_zone}\n",
        ]
        if existing:
            lines.append(f"FILTER_BY_ABSTRACT={existing}\n")
        PREFERENCES_FILE.write_text("".join(lines), encoding="utf-8")
    except OSError as e:
        print(f"[warn] 无法保存分区偏好: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# First-run interactive init helpers
# ---------------------------------------------------------------------------
# 首次运行的初始化交互为「三问式」：
#   Q1 选择文献库（可多选，选完即自动保存）
#   Q2 摘要自动筛选（两阶段：是否 → 仅此一次/以后都是，选完自动保存）
#   Q3 SCI 分区（两阶段：选区 → 仅此一次/以后都是，选完自动保存）
# 选择结果由程序直接写入 resources/config/ 下的配置文件，无需用户手动改。


def _ask_choice(prompt: str, options: dict[str, str], default: str) -> str | None:
    """Ask a single multiple-choice question, return the option KEY.

    options maps the canonical key (e.g. "1", "2") to a user-visible label
    (e.g. "一区", "二区"). The user may answer with the key, the label, or a
    digit; the matching option's key is returned. `default` is the key used
    on empty input. Returns None when stdin hits EOF (non-interactive), so
    callers can skip initialization instead of silently applying a default.
    """
    try:
        raw = input(prompt).strip().lower()
    except EOFError:
        # 非交互环境（AI agent / 管道）：无人应答。返回 None，调用方据此跳过
        # 初始化而非静默采用默认值，避免把无人确认的偏好落盘。
        return None
    if raw == "":
        return default
    for key, val in options.items():
        if raw == key.lower() or raw == val.lower():
            return key
    return default


def _ask_always_once() -> str | None:
    """Second-stage question: 仅此一次 / 以后都是.

    Returns 'once' or 'always', or None when stdin is non-interactive (EOF).
    """
    key = _ask_choice(
        "仅此一次，还是以后都是？[1=仅此一次 / 2=以后都是, 默认 2]: ",
        {"1": "once", "2": "always"},
        "2",
    )
    if key is None:
        return None
    return "once" if key == "1" else "always"



# ---------------------------------------------------------------------------
# SCI journal zone (中科院分区) filter
# ---------------------------------------------------------------------------
# Zone data lives in a local JSON map resources/data/journal_zones.json
# {"Journal Name": 1} where value is the 中科院大类分区 (1-4).
# It is maintained by the user (e.g. from LetPub / 中科院分区官网). The map
# is matched against each result's journal name with normalization, so the
# zone of a known journal is looked up even if the string differs slightly.


def load_journal_zones() -> dict[str, int]:
    """Load the local 中科院分区 map {journal_name: zone(1-4)}.

    Returns an empty dict if the file is missing or malformed, so the zone
    filter degrades gracefully (all papers pass, annotated as 无分区).
    """
    try:
        if not JOURNAL_ZONES_FILE.exists():
            return {}
        data = json.loads(JOURNAL_ZONES_FILE.read_text(encoding="utf-8"))
        zones: dict[str, int] = {}
        for name, z in data.items():
            if isinstance(z, (int, float)) and 1 <= int(z) <= 4:
                zones[str(name)] = int(z)
        return zones
    except Exception as e:
        print(f"[warn] 分区映射表读取失败: {e}", file=sys.stderr)
        return {}


def _norm_journal(name: str) -> str:
    """Normalize a journal name for lookup: lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", (name or "")).strip().lower()


def journal_zone(journal_name: str, zones: dict[str, int]) -> int | None:
    """Look up the 中科院分区 (1-4) of a journal name.

    Matching strategy (cheap, no external calls):
      1. exact normalized match against the map keys;
      2. contains-match: a map key is a substring of the journal name
         (e.g. key "advanced functional materials" matches
         "Advanced Functional Materials (Weinheim)").
    Returns None when unknown.
    """
    if not journal_name or not zones:
        return None
    target = _norm_journal(journal_name)
    if not target:
        return None
    # exact
    if target in zones:
        return zones[target]
    # substring: map key contained in journal name
    for key, z in zones.items():
        if key and key in target:
            return z
    return None


def filter_by_zone(results: list[dict], min_zone: int | None, zones: dict[str, int]) -> tuple[list[dict], list[dict]]:
    """Split results into kept / dropped by 中科院分区.

    - min_zone is None -> everything kept.
    - A paper is kept if its journal zone <= min_zone (1 is best).
    - Papers with an unknown journal (no entry in the map) are KEPT and
      annotated zone=None so the user still sees them, just unlabelled.
    Returns (kept, dropped).
    """
    if min_zone is None:
        return results, []
    kept: list[dict] = []
    dropped: list[dict] = []
    for r in results:
        z = journal_zone(r.get("journal"), zones)
        r["zone"] = z  # attach for display
        if z is None or z <= min_zone:
            kept.append(r)
        else:
            dropped.append(r)
    return kept, dropped


def get_keys() -> dict[str, str]:
    """Discover API keys from multiple sources."""
    env_file = _read_env_file(CONFIG_FILE)

    scopus = (os.environ.get("SCOPUS_API_KEY", "")
              or env_file.get("SCOPUS_API_KEY", "")
              or _read_env_file(PYBIO_CFG).get("APIKey", "")
              or _json_get(LITDL_CRED, ("elsevier", "api_key"), ""))

    wos = (os.environ.get("WOS_API_KEY", "")
           or env_file.get("WOS_API_KEY", "")
           or _json_get(LITDL_CRED, ("wos", "api_key"), ""))

    # Optional keys: sources work without them but benefit from higher rate limits.
    s2 = os.environ.get("S2_API_KEY", "") or env_file.get("S2_API_KEY", "")
    ncbi = os.environ.get("NCBI_API_KEY", "") or env_file.get("NCBI_API_KEY", "")

    mailto = (os.environ.get("OPENALEX_MAILTO", "")
              or env_file.get("OPENALEX_MAILTO", "")
              or os.environ.get("CROSSREF_MAILTO", "")
              or "user@example.com")

    return {"scopus": scopus, "wos": wos, "s2": s2, "ncbi": ncbi, "mailto": mailto}


def _json_get(path: Path, keys: tuple, default: str = "") -> str:
    try:
        if not path.exists():
            return default
        d = json.loads(path.read_text(encoding="utf-8"))
        for k in keys:
            d = d.get(k, {}) if isinstance(d, dict) else {}
        return d if isinstance(d, str) else default
    except Exception:
        return default


# ---------------------------------------------------------------------------
# HTTP client: retries, User-Agent, and TLS-verify-by-default
# ---------------------------------------------------------------------------
#
# The original version disabled TLS certificate verification for *all* sources
# to work around a pybliometrics SSL issue. Disabling cert checks globally is a
# man-in-the-middle risk, so we flip the default: verify certificates on every
# request, and ONLY if a request fails with an SSL error do we retry it once
# with an unverified context (a targeted fallback for broken local TLS setups).

RETRIABLE_HTTP = {429, 500, 502, 503, 504}


def _ssl_ctx() -> ssl.SSLContext:
    """Unverified context, used only as a last-resort SSL fallback."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_get(url: str, headers: dict[str, str], timeout: int, ssl_ctx: ssl.SSLContext) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout) as r:
        return r.read()


def _get(url: str, headers: dict[str, str] | None = None, timeout: int = 30, retries: int = 3):
    """GET + parse JSON, with retry + backoff.

    - Verifies TLS certs by default; falls back to an unverified context once
      if a prior attempt raised an SSL error (local-TLS workaround).
    - Retries 429 / 5xx / transient network errors with exponential backoff.
    - Sends a User-Agent header (OpenAlex's polite pool, Elsevier and
      Clarivate all expect one).
    """
    keys = get_keys()
    ua = f"thesis-retrieval/1.0 (+mailto:{keys['mailto']})"
    headers = {"User-Agent": ua, "Accept": "application/json", **dict(headers or {})}
    verified = ssl.create_default_context()
    last_err: Exception | None = None

    for attempt in range(retries):
        # If a prior attempt hit an SSL error, retry with the unverified context.
        ctx = _ssl_ctx() if isinstance(last_err, ssl.SSLError) else verified
        try:
            return json.loads(_http_get(url, headers, timeout, ctx))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in RETRIABLE_HTTP and attempt < retries - 1:
                time.sleep(0.5 * (2 ** attempt))
                continue
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code} for {url.split('?')[0][:60]}: {body}") from e
        except (urllib.error.URLError, ssl.SSLError, OSError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(0.5 * (2 ** attempt))

    raise RuntimeError(f"request failed after {retries} attempts: {last_err}")


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

class OpenAlexSource:
    """OpenAlex works search (covers CrossRef/PubMed/arXiv deposits)."""

    name = "openalex"

    def search(self, query: str, limit: int, sort: str, mailto: str) -> list[dict]:
        sort_param = {
            "cited": "cited_by_count:desc",
            "date": "publication_date:desc",
            "relevance": "",
        }.get(sort, "")
        url = ("https://api.openalex.org/works?"
               f"filter=title_and_abstract.search:{urllib.parse.quote(query)}"
               f"&per-page={min(limit, 50)}&mailto={urllib.parse.quote(mailto)}")
        if sort_param:
            url += f"&sort={sort_param}"
        data = _get(url)
        out = []
        for w in data.get("results", []):
            loc = w.get("primary_location") or {}
            src = loc.get("source") or {}
            out.append({
                "title": w.get("title"),
                "authors": [a["author"]["display_name"] for a in (w.get("authorships") or [])[:10]],
                "year": w.get("publication_year"),
                "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                "journal": src.get("display_name"),
                "cited_by": w.get("cited_by_count"),
                "source": self.name,
                "id": w.get("id"),
                "abstract": _reconstruct_abstract(w.get("abstract_inverted_index")),
            })
        return out


class ScopusSource:
    """Scopus search via direct Elsevier API (bypasses pybliometrics SSL bug)."""

    name = "scopus"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, limit: int, sort: str = "") -> list[dict]:
        if not self.available():
            raise RuntimeError("Scopus API key missing. Set SCOPUS_API_KEY or fix config.env")
        url = ("https://api.elsevier.com/content/search/scopus?"
               f"query={urllib.parse.quote(query)}&count={min(limit, 25)}&view=STANDARD")
        headers = {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}
        data = _get(url, headers)
        out = []
        for e in (data.get("search-results", {}).get("entry") or []):
            if "dc:title" not in e:
                continue
            out.append({
                "title": e.get("dc:title"),
                "authors": _scopus_authors(e),
                "year": _year(e.get("prism:coverDate", "")),
                "doi": e.get("prism:doi"),
                "journal": e.get("prism:publicationName"),
                "cited_by": _int(e.get("citedby-count")),
                "source": self.name,
                "id": e.get("dc:identifier"),
                "eid": e.get("eid"),
                # Scopus abstracts need view=COMPLETE (costs ~2x API credits);
                # skipped by default to keep the free tier cheap.
                "abstract": None,
            })
        return out


class WosSource:
    """Web of Science search via Clarivate WoS Starter API."""

    name = "wos"
    _BOOLEAN_OPS = {"OR", "AND", "NOT", "NEAR", "SAME"}
    MAX_OR_SPLIT = 10

    def __init__(self, api_key: str):
        self.api_key = api_key

    def available(self) -> bool:
        return bool(self.api_key)

    def _request(self, wos_q: str, limit: int) -> list[dict]:
        """Single WoS Starter API request and hit parsing."""
        url = ("https://api.clarivate.com/apis/wos-starter/v1/documents?"
               f"q={urllib.parse.quote(wos_q)}&limit={min(limit, 50)}&page=1")
        headers = {"X-ApiKey": self.api_key, "Accept": "application/json"}
        data = _get(url, headers)
        out = []
        for h in data.get("hits", []):
            src = h.get("source", {})
            names = h.get("names", {}) or {}
            ids = h.get("identifiers", {}) or {}
            out.append({
                "title": h.get("title"),
                "authors": [a.get("displayName") for a in (names.get("authors") or [])],
                "year": src.get("publishYear"),
                "doi": ids.get("doi"),
                "journal": src.get("sourceTitle"),
                "cited_by": _cited_by(h.get("citations")),
                "source": self.name,
                "id": h.get("uid"),
                # WoS Starter API does not return abstracts at all (v1/v2);
                # the cross-source dedupe may fill it from OpenAlex/CrossRef.
                "abstract": None,
            })
        return out

    def search(self, query: str, limit: int) -> list[dict]:
        if not self.available():
            raise RuntimeError("WoS API key missing. Set WOS_API_KEY or fix config.env")
        parts = self._split_or_terms(query)
        if not parts:
            # No top-level OR: single request.
            return self._request(self._to_wos_query(query), limit)

        # Top-level OR: split into one request per term, merge hits.
        results: list[dict] = []
        errors: list[str] = []
        for part in parts:
            try:
                results.extend(self._request(self._to_wos_query(part), limit))
            except Exception as e:
                errors.append(f'wos 子查询 "{part}" 失败: {e}')
                print(f"[warn] {errors[-1]}", file=sys.stderr)
        if not results and errors:
            raise RuntimeError("; ".join(errors))
        return results

    @staticmethod
    def _to_wos_query(query: str) -> str:
        """Convert a plain keyword query to WoS Starter API syntax.

        WoS 'q' field requires explicit field tags like TS=(), TI=(), etc.
        If the query already contains a field tag (e.g. 'TS=(x)' or 'AU=Smith'),
        pass it through. Otherwise wrap the whole thing in TS=() (topic search),
        joining bare terms with AND. Boolean operators (OR/AND/NOT/NEAR/SAME)
        are kept as operators, NOT treated as words, so queries like
        "silver AND gold" produce TS=(silver AND gold) instead of the
        invalid TS=(silver AND AND AND gold) which WoS rejects with 400.
        """
        q = query.strip()
        if re.search(r"\b(TS|TI|AB|AU|SO|PY|DO)\s*=", q, re.IGNORECASE):
            return q
        terms = re.findall(r'"([^"]+)"|(\S+)', q)
        parts = []
        for phrase, word in terms:
            if phrase:
                parts.append(f'"{phrase}"')
            elif word.upper() in WosSource._BOOLEAN_OPS:
                parts.append(word)  # operator: keep as-is, no AND around it
            else:
                parts.append(word)
        # Join terms with AND, but do not let AND double up (operator AND or
        # term ending with AND would produce 'AND AND AND').
        joined = ""
        for part in parts:
            if part.upper() in WosSource._BOOLEAN_OPS:
                joined = (joined + " " + part).strip()
            else:
                if joined and not joined.endswith(("AND", "OR", "NOT", "NEAR", "SAME")):
                    joined += " AND"
                joined += " " + part
        joined = joined.strip()
        return f"TS=({joined})" if joined else f"TS=({q})"

    @staticmethod
    def _split_or_terms(query: str) -> list[str] | None:
        """Split a query at top-level ORs (outside quotes and parentheses).

        Returns the list of leaf sub-queries when a top-level OR exists
        (nested parenthesised ORs are flattened recursively), else None.
        ORs inside quotes or inside parentheses (incl. field tags like
        TS=(a OR b)) are left untouched and the whole query passes through.
        """
        def scan(q: str) -> list[str]:
            # Split q at top-level OR (depth 0, outside quotes).
            splits: list[str] = []
            buf: list[str] = []
            in_quote = False
            depth = 0
            i = 0
            n = len(q)
            while i < n:
                c = q[i]
                if c == '"':
                    in_quote = not in_quote
                    buf.append(c)
                    i += 1
                    continue
                if not in_quote and c == "(":
                    depth += 1
                    buf.append(c)
                    i += 1
                    continue
                if not in_quote and c == ")":
                    depth -= 1
                    buf.append(c)
                    i += 1
                    continue
                # Top-level OR word (depth 0, outside quotes)
                if not in_quote and depth == 0 and (c == " " or c == "\t"):
                    j = i
                    while j < n and q[j] in " \t":
                        j += 1
                    if q[j:j + 2].upper() == "OR" and (j + 2 >= n or not q[j + 2].isalnum()):
                        if buf and "".join(buf).strip():
                            splits.append("".join(buf).strip())
                        buf = []
                        i = j + 2
                        continue
                buf.append(c)
                i += 1
            if buf and "".join(buf).strip():
                splits.append("".join(buf).strip())
            return splits

        parts = scan(query)
        if len(parts) < 2:
            return None
        # Flatten nested parenthesised ORs recursively: (a) OR (b OR c) -> [a, b, c]
        leaves: list[str] = []
        for p in parts:
            if p.startswith("(") and p.endswith(")"):
                inner = p[1:-1].strip()
                sub = scan(inner)
                if len(sub) >= 2:
                    leaves.extend(sub)
                    continue
                # Single leaf group: strip the outer parens (a) -> a
                if inner:
                    leaves.append(inner)
                    continue
            leaves.append(p)
        if len(leaves) > WosSource.MAX_OR_SPLIT:
            print(f"[warn] WoS 查询含 {len(leaves)} 个 OR 分支，超过上限 {WosSource.MAX_OR_SPLIT}，按原样单次请求", file=sys.stderr)
            return None
        return leaves


class CrossrefSource:
    """CrossRef REST API (free, no key; mailto recommended for Polite Pool)."""

    name = "crossref"

    def search(self, query: str, limit: int, sort: str, mailto: str) -> list[dict]:
        rows = min(limit, 50)
        url = ("https://api.crossref.org/works?" +
               urllib.parse.urlencode({
                   "query.bibliographic": query,
                   "rows": rows,
                   "select": "title,author,issued,DOI,container-title,is-referenced-by-count,type,abstract",
                   "mailto": mailto,
               }))
        if sort == "cited":
            url += "&sort=is-referenced-by-count&order=desc"
        elif sort == "date":
            url += "&sort=published&order=desc"
        data = _get(url)
        out = []
        for item in (data.get("message", {}).get("items") or []):
            out.append({
                "title": _first(item.get("title")),
                "authors": [a.get("family", "") + " " + a.get("given", "").strip() if a.get("given") else a.get("family", "")
                            for a in (item.get("author") or [])[:10]],
                "year": _year(_published(item)),
                "doi": item.get("DOI"),
                "journal": _first(item.get("container-title")),
                "cited_by": _int(item.get("is-referenced-by-count")),
                "source": self.name,
                "id": item.get("DOI"),
                "abstract": _clean_crossref_abstract(item.get("abstract")),
            })
        return out


class SemanticScholarSource:
    """Semantic Scholar search (free; optional key raises shared rate limit)."""

    name = "semantic_scholar"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, limit: int, sort: str) -> list[dict]:
        fields = "title,authors,year,externalIds,venue,citationCount,abstract"
        url = ("https://api.semanticscholar.org/graph/v1/paper/search?" +
               urllib.parse.urlencode({
                   "query": query,
                   "limit": min(limit, 100),
                   "fields": fields,
               }))
        if sort == "cited":
            url += "&sort=citationCount:desc"
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        data = _get(url, headers)
        out = []
        for p in (data.get("data") or []):
            ext = p.get("externalIds") or {}
            out.append({
                "title": p.get("title"),
                "authors": [a.get("name") for a in (p.get("authors") or [])],
                "year": p.get("year"),
                "doi": ext.get("DOI"),
                "journal": p.get("venue"),
                "cited_by": _int(p.get("citationCount")),
                "source": self.name,
                "id": p.get("paperId"),
                "abstract": p.get("abstract"),
            })
        return out


class PubmedSource:
    """PubMed via NCBI E-utilities (free; optional key raises limit from 3 to 10 rps)."""

    name = "pubmed"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, limit: int) -> list[dict]:
        # 1) esearch to get PMIDs
        esearch = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" +
                   urllib.parse.urlencode({
                       "db": "pubmed", "term": query,
                       "retmode": "json", "retmax": min(limit, 25),
                       **({"api_key": self.api_key} if self.api_key else {}),
                   }))
        id_data = _get(esearch)
        pmids = id_data.get("esearchresult", {}).get("idlist") or []
        if not pmids:
            return []

        # 2) esummary for metadata
        esummary = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" +
                    urllib.parse.urlencode({
                        "db": "pubmed", "id": ",".join(pmids), "retmode": "json",
                        **({"api_key": self.api_key} if self.api_key else {}),
                    }))
        sum_data = _get(esummary)
        out = []
        for pm in pmids:
            doc = sum_data.get("result", {}).get(pm) or {}
            if not doc:
                continue
            out.append({
                "title": doc.get("title"),
                "authors": [a.get("name") for a in (doc.get("authors") or [])],
                "year": _year(doc.get("pubdate", "")),
                "doi": _first(doc.get("elocationid"))  # stores 'doi: 10.xxxx'
                    .replace("doi:", "").strip() if doc.get("elocationid") else "",
                "journal": doc.get("fulljournalname") or doc.get("source"),
                "cited_by": None,  # PubMed does not expose citation counts
                "source": self.name,
                "id": pm,
                # PubMed abstracts require an extra efetch request per PMID;
                # skipped by default (keep the free tier cheap).
                "abstract": None,
            })
        return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reconstruct_abstract(inverted: dict | None) -> str | None:
    """Rebuild abstract text from OpenAlex's abstract_inverted_index.

    The index maps each word to a list of positions (0-based). We place words
    into an array by position and join with spaces, preserving original casing.
    """
    if not inverted:
        return None
    try:
        size = max(max(pos) for pos in inverted.values() if pos) + 1
    except ValueError:
        return None
    words = [""] * size
    for word, positions in inverted.items():
        for p in positions:
            if 0 <= p < size:
                words[p] = word
    text = " ".join(words).strip()
    return text or None


_JATS_TAG = re.compile(r"<[^>]+>")


def _clean_crossref_abstract(raw: str | None) -> str | None:
    """Strip JATS XML tags from a CrossRef abstract, turning <jats:p> into newlines.

    CrossRef stores abstracts with JATS markup (e.g. <jats:p>...<jats:sub>2</jats:sub>).
    Paragraph boundaries become newlines so the text does not run together.
    """
    if not raw:
        return None
    # Replace paragraph close tags with newline so multi-paragraph abstracts keep
    # their structure.
    s = re.sub(r"</\s*jats:p\s*>", "\n", raw)
    s = _JATS_TAG.sub("", s)
    # Collapse whitespace runs but keep paragraph newlines.
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n\n", s)
    s = s.replace("\n ", "\n")
    s = s.strip()
    return s or None


def _scopus_authors(e: dict) -> list[str]:
    authors = []
    for item in _as_list(e.get("author")):
        name = item.get("authname") or item.get("ce:indexed-name")
        if name:
            authors.append(name)
    creator = e.get("dc:creator")
    if not authors and creator:
        authors.append(creator)
    return authors


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def _first(v):
    """First element of a list, else the value itself (CrossRef wraps scalars in lists)."""
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _published(item: dict) -> str:
    """Best available publication date string from a CrossRef item."""
    for keys in (("published-print", "date-parts"), ("published-online", "date-parts"),
                 ("issued", "date-parts"), ("published", "date-parts"), ("posted", "date-parts")):
        if keys[0] in item and keys[1] in item.get(keys[0], {}):
            parts = item[keys[0]][keys[1]]
            if parts and parts[0]:
                return "-".join(str(x) for x in parts[0])
    return ""


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _cited_by(citations) -> int | None:
    """WoS hit-level citation count lives at citations[0]['count']."""
    if not citations:
        return None
    return _int(citations[0].get("count"))


def _year(date_str: str) -> int | None:
    m = re.match(r"(\d{4})", date_str or "")
    return int(m.group(1)) if m else None


def dedupe(results: list[dict]) -> list[dict]:
    """Deduplicate by normalized DOI, else by full normalized title.

    Sources are prepended in priority order (openalex > scopus > wos), so
    keeping the first occurrence naturally preserves that priority.
    Comparing the *full* normalized title (case- and whitespace-insensitive)
    instead of a fixed 80-char prefix avoids wrongly merging distinct papers
    that happen to share a long leading phrase.
    """
    seen: set[str] = set()
    out = []
    for r in results:
        key = ""
        doi = (r.get("doi") or "").strip().lower()
        if doi:
            key = f"doi:{doi}"
        else:
            t = re.sub(r"\s+", "", (r.get("title") or "").lower())
            if t:
                key = f"title:{t}"
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def fill_abstracts(results: list[dict]) -> list[dict]:
    """Backfill abstracts across sources by DOI.

    WoS/Scopus/PubMed return no abstract in the default view; when the same
    paper (same DOI) was fetched from OpenAlex/CrossRef/Semantic Scholar, copy
    its abstract over so downstream filtering still works.
    """
    by_doi: dict[str, str] = {}
    for r in results:
        doi = (r.get("doi") or "").strip().lower()
        if doi and r.get("abstract"):
            by_doi.setdefault(doi, r["abstract"])
    for r in results:
        if not r.get("abstract"):
            doi = (r.get("doi") or "").strip().lower()
            if doi and doi in by_doi:
                r["abstract"] = by_doi[doi]
    return results


def sort_results(results: list[dict], sort: str) -> list[dict]:
    if sort == "cited":
        return sorted(results, key=lambda r: r.get("cited_by") or 0, reverse=True)
    if sort == "date":
        return sorted(results, key=lambda r: r.get("year") or 0, reverse=True)
    return results


def print_results(results: list[dict], source_filter: str | None = None, show_abstracts: bool = False,
                  show_zone: bool = False):
    for r in results:
        if source_filter and r.get("source") != source_filter:
            continue
        yr = r.get("year") or "?"
        cited = r.get("cited_by") or 0
        src = r.get("source", "")
        jn = (r.get("journal") or "")[:28]
        t = (r.get("title") or "")[:72]
        doi = r.get("doi") or ""
        zone = ""
        if show_zone:
            z = r.get("zone")
            zone = f" | 分区={z}" if z else " | 分区=?"
        print(f"[{yr}] {t} | {jn} | src={src} | cit={cited}{zone} | {doi}")
        if show_abstracts:
            ab = (r.get("abstract") or "").strip()
            if ab:
                print(f"    abstract: {ab[:300]}{'...' if len(ab) > 300 else ''}")
            else:
                print(f"    abstract: (无)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def resolve_sources(args, keys) -> list[str]:
    """Return the list of sources to search, prompting interactively if needed.

    Priority:
      1. Explicit `--sources` is honoured verbatim (no prompt, nothing saved).
      2. Otherwise, a previously saved selection (resources/config/sources.env)
         is used silently.
      3. Otherwise (first run), a numbered multi-select menu is shown; after
         picking, the user is asked whether to save the choice for future runs.
    """
    valid = set(ALL_SOURCES)
    if args.sources is not None:
        picked = [s.strip() for s in args.sources.split(",") if s.strip()]
        picked = [s for s in picked if s in valid]
        if args.save_sources and picked:
            save_sources(picked)  # 显式 --sources 时也允许 --save-sources 持久化
        return picked

    saved = load_saved_sources()
    if saved:
        if args.save_sources:
            save_sources(saved)  # 显式 --save-sources 时重写一次（幂等）
        return saved

    available_by_key = {
        "openalex": True,              # never requires a key
        "crossref": True,              # never requires a key
        "semantic_scholar": True,      # key optional
        "pubmed": True,                # key optional
        "scopus": bool(keys["scopus"]),
        "wos": bool(keys["wos"]),
    }

    def _flag(s: str) -> str:
        if available_by_key.get(s, True):
            return ""
        return "  (缺 key，选中会被跳过)"

    print("首次运行：请选择要检索的学术库（可多选，逗号或空格分隔）：")
    for i, s in enumerate(ALL_SOURCES, 1):
        print(f"  [{i}] {s:<8} {SOURCE_HINTS.get(s, '')}{_flag(s)}")
    print("  all = 全部（跳过缺 key 的库）    [默认回车 = 全部可用的库]")

    try:
        raw = input("选择 [1,2,3 / all / Enter]: ").strip()
    except EOFError:
        # AI agent / 管道 / 计划任务等非交互环境无法弹菜单：中止并提示，绝不自动
        # 落盘默认库，避免把无人确认的默认持久化。须真人在终端跑过一次初始化。
        print("\n[需要人工初始化] 本 skill 首次运行需在真实终端由人选择文献库并确认。\n"
              "请在你的终端运行一次：\n"
              "    python scripts/thesis_retrieval.py \"test\"\n"
              "走完三问式初始化后，AI 即可调用。或临时用 --sources 指定库（不落盘）。",
              file=sys.stderr)
        return []

    if not raw or raw.lower() == "all":
        picks = [s for s in ALL_SOURCES if available_by_key.get(s, True)]
    else:
        picked = []
        for token in re.split(r"[, ]+", raw):
            token = token.strip().lower()
            if token in valid:
                picked.append(token)
            elif token.isdigit():
                n = int(token)
                if 1 <= n <= len(ALL_SOURCES):
                    picked.append(ALL_SOURCES[n - 1])
        picks = list(dict.fromkeys(s for s in picked if s in valid))

    if not picks:
        return []

    # 首次初始化：选择结果直接自动保存，不再单独询问是否保存
    save_sources(picks)
    print(f"已保存到 resources/config/sources.env。想换库：改该文件、删除后重跑，或加 --sources。")
    return picks


def cmd_check_keys():
    keys = get_keys()
    print(f"OpenAlex        : free (no key)  mailto={keys['mailto']}")
    print(f"Crossref        : free (no key)  mailto={keys['mailto']}")
    print(f"SemanticScholar : free (no key)  S2_API_KEY={'[set]' if keys['s2'] else '(optional)'}")
    print(f"PubMed (NCBI)   : free (no key)  NCBI_API_KEY={'[set]' if keys['ncbi'] else '(optional)'}")
    print(f"Scopus API key  : {'[set]' if keys['scopus'] else '[missing]'}")
    print(f"WoS API key     : {'[set]' if keys['wos'] else '[missing]'}")
    if not keys["scopus"] and not keys["wos"]:
        print("\nScopus/WoS require a key. Configure resources/config/config.env:")
        print("  SCOPUS_API_KEY=...")
        print("  WOS_API_KEY=...")


SOURCE_DETAILS = {
    "openalex": {
        "覆盖": "CrossRef + PubMed + arXiv 收录",
        "凭据": "免 key（建议 OPENALEX_MAILTO 进 polite pool）",
        "限流/说明": "免费，默认源",
        "查询语法": "普通关键词即 title+abstract 全文搜索；引号做精确短语",
    },
    "crossref": {
        "覆盖": "全球 DOI 元数据（几乎全部期刊论文）",
        "凭据": "免 key（建议 CROSSREF_MAILTO）",
        "限流/说明": "免费，含被引数",
        "查询语法": "query.bibliographic 书目检索，接受普通关键词",
    },
    "semantic_scholar": {
        "覆盖": "跨学科，AI 领域强",
        "凭据": "免 key；可选 S2_API_KEY 提升共享限流",
        "限流/说明": "无 key 共享限流（高峰可能 429），含被引数",
        "查询语法": "普通关键词即可",
    },
    "pubmed": {
        "覆盖": "生物医学",
        "凭据": "免 key；可选 NCBI_API_KEY 提升 3→10 rps",
        "限流/说明": "无 key 限 3 rps，无被引数",
        "查询语法": "普通关键词传 NCBI esearch，支持字段标签/布尔",
    },
    "scopus": {
        "覆盖": "Elsevier 全库",
        "凭据": "必填 SCOPUS_API_KEY",
        "限流/说明": "每源最大 25 条",
        "查询语法": "接受 Scopus 高级检索语法，如 TITLE-ABS-KEY(...)",
    },
    "wos": {
        "覆盖": "Clarivate 核心合集",
        "凭据": "必填 WOS_API_KEY",
        "限流/说明": "WoS Starter API（每源最大 50 条）",
        "查询语法": "自动包装为 TS=(...)；已含字段标签（TS=/TI=/AU=/SO=）则原样传递",
    },
}


def cmd_list_sources():
    """Print per-source coverage / credentials / tips. Replaces the info table
    that used to live in SKILL.md so agents can query it at runtime."""
    keys = get_keys()
    print("可用检索源（thesis-retrieval 1.1.1）：")
    for name in ALL_SOURCES:
        d = SOURCE_DETAILS.get(name, {})
        print(f"\n[{name}]")
        for k, v in d.items():
            print(f"  {k}: {v}")
    print("\nkey 配置位置：环境变量 → resources/config/config.env → 其他（见 --check-keys）")
    print("提示：--sources 控制查哪些库；--source 只过滤显示。运行 --help 看全部参数。")


def main():
    ap = argparse.ArgumentParser(description="Unified multi-source academic paper search")
    ap.add_argument("query", nargs="?", help="Search query")
    ap.add_argument("--sources", default=None,
                    help="Comma-separated sources: openalex,crossref,semantic_scholar,pubmed,scopus,wos. "
                         "Omit to use saved config or choose interactively (multi-select).")
    ap.add_argument("--save-sources", action="store_true",
                    help="Save the chosen/saved sources as the persistent default (sources.env)")
    ap.add_argument("--source", dest="source", help="Single source filter for output")
    ap.add_argument("--limit", type=int, default=10, help="Max results per source (default 10)")
    ap.add_argument("--sort", choices=["relevance", "cited", "date"], default="relevance")
    ap.add_argument("--out", help="Write results to JSON file (always includes abstract)")
    ap.add_argument("--abstracts", action="store_true",
                    help="Also print abstracts in the text output")
    ap.add_argument("--filter", choices=["always", "once", "no", "never"],
                    help="Abstract-based relevance filter: always=save default (filter every time), "
                         "once=filter this run only, no=don't filter this run, "
                         "never=don't filter and never ask again. Omit to use saved preference.")
    ap.add_argument("--zone", type=int, choices=[1, 2, 3, 4], default=None,
                    help="SCI 中科院分区下限：只保留分区 <= 该值的文献（1 区最高）。"
                         "配合 --zone-mode always|once 决定是否保存为默认。缺省用保存的偏好。")
    ap.add_argument("--zone-mode", choices=["always", "once", "off"], default=None,
                    help="分区筛选模式：always=保存为默认（以后都这样），once=仅本次，off=本次不用。"
                         "缺省用保存的偏好（无保存时首次交互询问）。")
    ap.add_argument("--check-keys", action="store_true", help="Verify API keys and exit")
    ap.add_argument("--list-sources", action="store_true",
                    help="List all sources, their credentials and query syntax, then exit")
    ap.add_argument("--version", action="version", version="thesis-retrieval 1.1.1")
    args = ap.parse_args()

    if args.check_keys:
        cmd_check_keys()
        return

    if args.list_sources:
        cmd_list_sources()
        return

    if not args.query:
        ap.print_help()
        return

    keys = get_keys()
    sources = resolve_sources(args, keys)
    if not sources:
        print("未选择任何有效的检索库（openalex/scopus/wos）。", file=sys.stderr)
        return

    # Abstract-based relevance filter preference:
    #   --filter        explicit override (always/once/no/never)
    #   preferences.env saved value
    #   else first run: ask the user (two-stage: 是否 → 仅此一次/以后都是)
    filter_pref = args.filter
    if not filter_pref:
        filter_pref = load_filter_pref()
    if not filter_pref:
        ans = _ask_choice(
            "\n是否按摘要自动筛选文献（读摘要判断每篇是否贴合需求）？[y=是 / n=不是, 默认 是]: ",
            {"y": "是", "n": "不是"}, "y",
        )
        if ans is None:
            # 非交互环境（EOF）：本次按摘要筛选，不落盘偏好（首次初始化须真人完成）。
            filter_pref = "once"
        elif ans == "y":
            # 第二问：仅此一次 / 以后都是
            filter_pref = _ask_always_once()
            if filter_pref is None:
                # 第二问遇到 EOF：视为仅本次，不落盘。
                filter_pref = "once"
            elif filter_pref == "always":
                save_filter_pref("always")
                print("已保存：以后每次都按摘要筛选。想改：编辑 resources/config/preferences.env 或 --filter。")
            else:
                save_filter_pref("once")
                print("已保存：仅本次按摘要筛选（下次仍会询问）。")
        else:
            save_filter_pref("never")
            print("已保存：不用摘要筛选，也不再询问。想改：编辑 resources/config/preferences.env 或 --filter。")
    elif filter_pref in ("always", "never"):
        save_filter_pref(filter_pref)  # 显式 --filter always/never 也持久化为默认

    # SCI 中科院分区筛选偏好：
    #   --zone / --zone-mode   显式覆盖
    #   preferences.env 保存值（ZONE_FILTER + ZONE_MIN）
    #   否则首次运行交互询问
    zone_mode = args.zone_mode
    zone_min = args.zone
    if zone_mode is None and zone_min is None:
        saved_mode, saved_min = load_zone_pref()
        if saved_mode and saved_min:
            zone_mode, zone_min = saved_mode, saved_min
    if zone_mode == "off":
        zone_mode, zone_min = None, None
    elif zone_mode is None and zone_min is not None:
        zone_mode = "once"  # --zone 未给模式时默认仅本次
    elif zone_mode is not None and zone_min is None:
        zone_min = 2  # --zone-mode 未给分区时默认 2 区及以上
    elif zone_mode is None and zone_min is None:
        # 首次：询问用户（两阶段：选区 → 仅此一次/以后都是）
        zc = _ask_choice(
            "\nSCI 分区筛选：只保留哪个区及以上的文献？[1=一区 / 2=二区 / 3=三区 / 4=四区 / 0=全部, 默认 二区]: ",
            {"1": "一区", "2": "二区", "3": "三区", "4": "四区", "0": "全部"}, "2",
        )
        if zc is None:
            # 非交互环境（EOF）：本次不按分区筛选，不落盘偏好（首次初始化须真人完成）。
            zone_min = None
        elif zc == "0":
            zone_min = None
            print("本次不按分区筛选（不影响以后，下次仍会询问）。")
        else:
            zone_min = int(zc)
            # 第二问：仅此一次 / 以后都是
            zs = _ask_always_once()
            if zs is None:
                # 第二问遇到 EOF：视为仅本次，不落盘。
                pass
            elif zs == "always":
                save_zone_pref("always", zone_min)
                print(f"已保存：以后每次检索都按 {zone_min} 区及以上筛选。"
                      f"想改：编辑 resources/config/preferences.env 的 ZONE_FILTER/ZONE_MIN 行。")
            else:
                save_zone_pref("once", zone_min)
                print(f"已保存：仅本次按 {zone_min} 区及以上筛选（下次仍会询问）。")
    elif zone_mode == "always" and zone_min:
        save_zone_pref("always", zone_min)  # 显式 --zone-mode always 也持久化为默认

    zones = load_journal_zones()
    if zones and zone_min:
        print(f"[分区] 已加载 {len(zones)} 个期刊分区映射。", file=sys.stderr)

    results: list[dict] = []
    errors: list[str] = []

    if "openalex" in sources:
        try:
            oa = OpenAlexSource()
            results.extend(oa.search(args.query, args.limit, args.sort, keys["mailto"]))
        except Exception as e:
            errors.append(f"openalex: {e}")

    if "crossref" in sources:
        try:
            cf = CrossrefSource()
            results.extend(cf.search(args.query, args.limit, args.sort, keys["mailto"]))
        except Exception as e:
            errors.append(f"crossref: {e}")

    if "semantic_scholar" in sources:
        try:
            ss = SemanticScholarSource(keys["s2"])
            results.extend(ss.search(args.query, args.limit, args.sort))
        except Exception as e:
            errors.append(f"semantic_scholar: {e}")

    if "pubmed" in sources:
        try:
            pm = PubmedSource(keys["ncbi"])
            results.extend(pm.search(args.query, args.limit))
        except Exception as e:
            errors.append(f"pubmed: {e}")

    if "scopus" in sources:
        try:
            sc = ScopusSource(keys["scopus"])
            results.extend(sc.search(args.query, args.limit))
        except Exception as e:
            errors.append(f"scopus: {e}")

    if "wos" in sources:
        try:
            wos = WosSource(keys["wos"])
            results.extend(wos.search(args.query, args.limit))
        except Exception as e:
            errors.append(f"wos: {e}")

    results = dedupe(results)
    results = fill_abstracts(results)
    results = sort_results(results, args.sort)

    # Apply 中科院分区 filter (keeps papers with zone <= min_zone; unknown journals are kept, unlabelled)
    dropped: list[dict] = []
    if zone_min:
        results, dropped = filter_by_zone(results, zone_min, zones)
        if dropped:
            print(f"[分区] 过滤掉 {len(dropped)} 篇分区高于 {zone_min} 区的文献（见 --out 的 dropped）。",
                  file=sys.stderr)

    print_results(results, args.source, show_abstracts=args.abstracts, show_zone=bool(zone_min))

    if errors:
        print(f"\n# errors: {errors}", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"query": args.query, "results": results, "dropped": dropped, "errors": errors},
                      f, ensure_ascii=False, indent=2)
        print(f"\n[written] {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
