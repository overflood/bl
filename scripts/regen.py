# migrate_html_to_md.py (v6 – kompatibel mit openai>=1.0)
"""
Batch‑Migrator … (Docstring gekürzt)

▶️ Neu in **v6**
* unterstützt **openai‑python ≥ 1.0** (neues API‑Schema).
  * nutzt `openai_client.chat.completions.create`.  
  * fallback auf Legacy‑Import (0.28) bleibt möglich.
* GPT‑Aufruf jetzt in `gpt_optimize()` version‑agnostisch.
"""

from __future__ import annotations
import argparse, csv, difflib, os, sys, textwrap
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import frontmatter
from bs4 import BeautifulSoup
from slugify import slugify
from tqdm import tqdm

# ---------------------------------------------------------------------------
# OpenAI Setup (kompatibel zu >=1.0 & <1.0) ---------------------------------
# ---------------------------------------------------------------------------
GPT_AVAILABLE = False
new_client = None  # type: ignore
try:
    import openai  # >=1.0 importiert als package
    # Unterscheide: in >=1.0 gibt es openai.Client / openai.VERSION
    if hasattr(openai, "OpenAI"):
        new_client = openai.OpenAI()  # default liest OPENAI_API_KEY aus Env
        GPT_AVAILABLE = True
    else:
        # <=0.28 classic
        GPT_AVAILABLE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEGACY_ROOT  = PROJECT_ROOT / "static" / "legacy"
CONTENT_ROOT = PROJECT_ROOT / "content"
REPORT_CSV   = PROJECT_ROOT / "migration_report.csv"
DEFAULT_DIFF = 0.95
GPT_MODEL    = "gpt-4o-mini"
SYS_PROMPT   = (
    "Du bist ein pedantischer Markdown‑Linter. * Erhalte Inhalt & Reihenfolge. "
    "* Strukturiere Listen, Absätze, Tabellen semantisch sauber. * Entferne nichts "
    "und erfinde nichts. * Behalte Bilder und Links. Gib nur den bereinigten Markdown‑Text zurück."
)

@dataclass
class PageResult:
    legacy_html: Path
    md_path: Optional[Path]
    status: str
    note: str = ""

# ------------ helpers -------------------------------------------------------

def html_to_markdown(html: Path) -> str:
    import pypandoc
    try:
        return pypandoc.convert_file(str(html), "gfm", format="html")
    except OSError:
        pypandoc.download_pandoc()
        return pypandoc.convert_file(str(html), "gfm", format="html")

def md_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

def extract_images(html: Path) -> List[str]:
    soup = BeautifulSoup(html.read_text("latin1", errors="ignore"), "html.parser")
    return [img.get("src") or "" for img in soup.find_all("img")]

def copy_images(srcs: List[str], html: Path):
    for src in srcs:
        if src and not src.startswith("http"):
            src_abs  = html.parent / src
            dest_abs = LEGACY_ROOT / src_abs.relative_to(LEGACY_ROOT)
            if src_abs.exists() and not dest_abs.exists():
                dest_abs.parent.mkdir(parents=True, exist_ok=True)
                dest_abs.write_bytes(src_abs.read_bytes())

# GPT wrapper ----------------------------------------------------------------

def gpt_optimize(md: str) -> str:
    if not (GPT_AVAILABLE and os.getenv("OPENAI_API_KEY")):
        return md
    try:
        # new client (>=1.0)
        if new_client:
            resp = new_client.chat.completions.create(
                model=GPT_MODEL,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYS_PROMPT},
                    {"role": "user", "content": md[:120_000]},
                ],
            )
            return resp.choices[0].message.content.strip()
        # legacy openai<=0.28
        import openai  # type: ignore reimport ok
        resp = openai.ChatCompletion.create(
            model=GPT_MODEL,
            temperature=0,
            messages=[{"role":"system","content":SYS_PROMPT},
                      {"role":"user",  "content": md[:120_000]}],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ GPT übersprungen:", e)
        return md

# markdown writer ------------------------------------------------------------

def write_md(path: Path, content: str, legacy_rel: str):
    fm = frontmatter.Post("", **{
        "title": path.stem.replace("-"," ").title(),
        "draft": False,
        "aliases": [f"/{legacy_rel}.htm", f"/{legacy_rel}.html"],
        "categories": [path.parts[1] if len(path.parts)>1 else "misc"],
        "slug": slugify(path.stem),
    })
    fm.content = content.strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        frontmatter.dump(fm, f)

# core -----------------------------------------------------------------------

def process(html: Path, diff_thr: float, force: bool, use_gpt: bool) -> PageResult:
    rel = html.relative_to(LEGACY_ROOT).with_suffix("")
    md  = (CONTENT_ROOT / rel).with_suffix(".md")
    try:
        md_raw = html_to_markdown(html)
        copy_images(extract_images(html), html)
        md_new = gpt_optimize(md_raw) if use_gpt else md_raw

        if not md.exists():
            write_md(md, md_new, str(rel))
            return PageResult(html, md, "missing_md", "neu angelegt")

        if force or md_similarity(md.read_text("utf-8",errors="ignore"), md_new) < diff_thr:
            write_md(md, md_new, str(rel))
            return PageResult(html, md, "regenerated", f"Diff >{(1-diff_thr)*100:.0f}%")
        return PageResult(html, md, "OK")
    except Exception as ex:
        return PageResult(html, md if md.exists() else None, "error", str(ex))

# cli ------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--gpt", action="store_true")
    ap.add_argument("--diff", type=float)
    args = ap.parse_args()
    diff_thr = args.diff if args.diff else DEFAULT_DIFF

    html_files = sorted(LEGACY_ROOT.rglob("*.htm*"))
    print(f"Legacy-HTMLs: {len(html_files)} • Diff-Schwelle: {diff_thr:.2f}\n")

    results: List[PageResult] = []
    for html in tqdm(html_files, desc="Migrating"):
        results.append(process(html, diff_thr, args.force, args.gpt))

    with REPORT_CSV.open("w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["legacy_html","markdown","status","note"])
        for r in results:
            wr.writerow([
                r.legacy_html.relative_to(LEGACY_ROOT),
                r.md_path.relative_to(CONTENT_ROOT) if r.md_path else "–",
                r.status,
                r.note,
            ])

    summary = Counter(r.status for r in results)
    print("\nSummary:")
    for k in ("OK","missing_md","regenerated","error"):
        if summary[k]:
            print(f"  {k:<12}: {summary[k]}")
    print("\nReport →", REPORT_CSV)

if __name__ == "__main__":
    main()
