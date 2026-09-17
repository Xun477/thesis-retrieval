# Install thesis-retrieval (for AI agents)

`thesis-retrieval` is a multi-source academic paper search skill (OpenAlex / CrossRef / Semantic Scholar / PubMed / Scopus / Web of Science). This document is written for AI agents: install it fast, no human-facing fluff.

## TL;DR

```bash
# 1. Locate the skill dir for this harness (usually global):
ls -d ~/.claude ~/.codex ~/.agents 2>/dev/null   # pick the one that exists

# 2. Clone into it (recommended; git pull = update):
git clone https://github.com/Xun477/thesis-retrieval ~/.claude/skills/thesis-retrieval

# 3. Verify:
cd ~/.claude/skills/thesis-retrieval
python scripts/thesis_retrieval.py --version    # expect: thesis-retrieval 1.1.6
python scripts/thesis_retrieval.py --check-keys # expect: 4 free sources + scopus/wos key status
```

Done. Core search needs Python 3.9+ only (stdlib, zero third-party deps).

## Steps

### 1. Target directory

| Harness | Skill dir |
| :-- | :-- |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| Pi / OpenCode | `~/.agents/skills/` |

Install into the **global** dir above unless the user explicitly wants project-local. Windows: `%USERPROFILE%\.claude\skills\`.

### 2. Get the skill

Preferred — clone (updatable via `git pull`):

```bash
git clone https://github.com/Xun477/thesis-retrieval "$TARGET/thesis-retrieval"
```

Alternative — copy an existing checkout:

```bash
cp -R /path/to/thesis-retrieval "$TARGET/thesis-retrieval"
```

Verify files landed:

```bash
ls "$TARGET/thesis-retrieval"/SKILL.md "$TARGET/thesis-retrieval"/scripts/thesis_retrieval.py
```

### 3. Credentials (optional)

4 sources are key-free: openalex / crossref / semantic_scholar / pubmed.
Scopus and WoS need keys; without them they are skipped automatically.

Keys are read from env vars first, then `resources/config/config.env`:

```bash
# optional but recommended (raise rate limits):
export OPENALEX_MAILTO=you@example.com
export SCOPUS_API_KEY=...   # only if user has one
export WOS_API_KEY=...      # only if user has one; approval takes 1-3+ business days
```

Or copy the template and fill it in:

```bash
cp resources/config/config.env resources/config/config.local.env   # git-ignored
```

### 4. First run (mandatory, human step)

The first run **must** be done by a human in a real terminal — a three-question init (pick sources → abstract filter → SCI zone) writes `sources.env` / `preferences.env`:

```bash
python scripts/thesis_retrieval.py "test"
```

If running in a non-interactive environment (agent Bash / pipe) with no config, the script aborts with "需要人工初始化" — open a real terminal and run the command above, or invoke the launcher:

```bash
python scripts/init_config.py   # opens a real terminal window and waits
```

Do **not** work around it with `--sources` (that skips init and persists nothing).

### 5. Verify

```bash
cd "$TARGET/thesis-retrieval"
python scripts/thesis_retrieval.py --version      # thesis-retrieval 1.1.6
python scripts/thesis_retrieval.py --check-keys   # all source key status
```

Optional extras: WoS screenshot+OCR fallback needs `pip install playwright rapidocr_onnxruntime`; see SKILL.md.
