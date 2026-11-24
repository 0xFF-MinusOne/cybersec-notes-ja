#!/usr/bin/env python3
"""GitBook 形式の Markdown を MkDocs 用に変換して .site-src/ へ出力する。

元のファイルは書き換えない。使い方:
    python tools/prepare_docs.py            # .site-src/ を作り直す
    python tools/prepare_docs.py --nav      # SUMMARY.md から nav (YAML) を表示する

変換するもの(コードブロックの中は変換しない):
    {% hint style="..." %}   -> !!! note/tip/warning/danger
    {% file src=".." %}      -> ダウンロードリンク(ファイルが無ければキャプションのみ)
    {% embed url=".." %}     -> リンク
    {% tabs %}/{% tab %}     -> === "タイトル"
    {% code title=".." %}    -> コードフェンスの title 属性
    <details>                -> <details markdown="1">
変換できない {% ... %} はそのまま残す。
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".site-src"
SECTIONS = ["binexp", "rev"]
ASSETS_DIR = "gitbook-assets"
TOP_FILES = ["README.md", "GLOSSARY.md"]
HINT_KINDS = {"info": "note", "success": "tip", "warning": "warning", "danger": "danger"}
# 囲みの見出し(日本語)。GitBook の style 名 → 表示する見出し
HINT_TITLES = {"info": "情報", "success": "ヒント", "warning": "注意", "danger": "危険"}

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
HINT_OPEN = re.compile(r'^(\s*)\{%\s*hint(?:\s+style="([^"]*)")?\s*%\}\s*$')
TABS_OPEN = re.compile(r'^(\s*)\{%\s*tabs\s*%\}\s*$')
TAB_OPEN = re.compile(r'^(\s*)\{%\s*tab\s+title="((?:[^"\\]|\\.)*)"\s*%\}\s*$')
CODE_OPEN = re.compile(r'^\s*\{%\s*code\b(.*?)%\}\s*$')
CODE_END = re.compile(r'^\s*\{%\s*endcode\s*%\}\s*$')
FILE_END = re.compile(r'^\s*\{%\s*endfile\s*%\}\s*$')
FILE_TAG = re.compile(r'\{%\s*file\s+([^%]*?)\s*%\}')
EMBED_TAG = re.compile(r'\{%\s*embed\s+([^%]*?)\s*%\}')
ATTR_RE = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')


def fence_flags(lines):
    """各行が(開始・終了行を含む)コードブロック内なら True。"""
    flags, fence = [], None
    for ln in lines:
        m = FENCE_RE.match(ln)
        if fence is None:
            if m:
                fence = (m.group(1)[0], len(m.group(1)))
                flags.append(True)
            else:
                flags.append(False)
        else:
            flags.append(True)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1] and not m.group(2).strip():
                fence = None
    return flags


def find_end(lines, flags, start, open_re, name):
    """start の開始タグに対応する {% endNAME %} の行番号。見つからなければ -1。"""
    end_re = re.compile(r'^\s*\{%\s*end' + name + r'\s*%\}\s*$')
    depth = 0
    for i in range(start, len(lines)):
        if flags[i]:
            continue
        if open_re.match(lines[i]):
            depth += 1
        elif end_re.match(lines[i]):
            depth -= 1
            if depth == 0:
                return i
    return -1


def indent(lines, prefix):
    return [(prefix + ln) if ln.strip() else "" for ln in lines]


def attrs(s):
    return {k: v.replace('\\"', '"') for k, v in ATTR_RE.findall(s)}


def unescape(s):
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!|<>~])", r"\1", s)


TYPES_LINK = re.compile(r"\]\(((?:\.\./)+)types/([^)#\s]*)")


def types_sub(mm, srcdir, stats):
    """旧名 types/ へのリンクを、実在する binexp/ に張り替える。"""
    new = (srcdir / (mm.group(1) + "binexp/" + mm.group(2))).resolve()
    if new.exists():
        stats["types_link"] += 1
        return "](%sbinexp/%s" % (mm.group(1), mm.group(2))
    return mm.group(0)


def convert(lines, srcdir, stats):
    flags = fence_flags(lines)
    out = []

    def ensure_blank():
        if out and out[-1].strip():
            out.append("")

    pending_code = None
    i = 0
    while i < len(lines):
        ln = lines[i]
        if flags[i]:
            m = FENCE_RE.match(ln)
            if pending_code is not None and m and (i == 0 or not flags[i - 1]):
                lead = ln[: len(ln) - len(ln.lstrip())]
                info = m.group(2).strip()
                a = pending_code
                extra = []
                if a.get("title"):
                    extra.append('title="%s"' % a["title"].replace('"', "'"))
                if a.get("lineNumbers") == "true":
                    extra.append('linenums="1"')
                if extra:
                    lang = info.split()[0] if info and not info.startswith("{") else ("text" if not info else "")
                    rest = info[len(lang):].strip() if lang and info else ""
                    ln = "%s%s%s %s" % (lead, m.group(1), lang or "", " ".join(([rest] if rest else []) + extra)) if lang else ln
                pending_code = None
            out.append(ln)
            i += 1
            continue

        m = CODE_OPEN.match(ln)
        if m:
            pending_code = attrs(m.group(1))
            stats["code"] += 1
            i += 1
            continue
        if CODE_END.match(ln) or FILE_END.match(ln):
            i += 1
            continue

        m = HINT_OPEN.match(ln)
        if m:
            end = find_end(lines, flags, i, HINT_OPEN, "hint")
            if end > 0:
                style = m.group(2) or "info"
                kind = HINT_KINDS.get(style, "note")
                inner = convert(lines[i + 1:end], srcdir, stats)
                while inner and not inner[0].strip():
                    inner.pop(0)
                while inner and not inner[-1].strip():
                    inner.pop()
                ensure_blank()
                out.append('%s!!! %s "%s"' % (m.group(1), kind, HINT_TITLES.get(style, "情報")))
                out.append("")
                out.extend(indent(inner, m.group(1) + "    "))
                out.append("")
                stats["hint"] += 1
                i = end + 1
                continue

        m = TABS_OPEN.match(ln)
        if m:
            end = find_end(lines, flags, i, TABS_OPEN, "tabs")
            if end > 0:
                body = lines[i + 1:end]
                bflags = fence_flags(body)
                ensure_blank()
                j = 0
                while j < len(body):
                    tm = None if bflags[j] else TAB_OPEN.match(body[j])
                    if not tm:
                        j += 1
                        continue
                    tend = find_end(body, bflags, j, TAB_OPEN, "tab")
                    if tend < 0:
                        tend = len(body)
                    inner = convert(body[j + 1:tend], srcdir, stats)
                    while inner and not inner[0].strip():
                        inner.pop(0)
                    while inner and not inner[-1].strip():
                        inner.pop()
                    title = tm.group(2).replace('\\"', "'").replace('"', "'")
                    out.append('%s=== "%s"' % (m.group(1), title))
                    out.append("")
                    out.extend(indent(inner, m.group(1) + "    "))
                    out.append("")
                    stats["tab"] += 1
                    j = tend + 1
                stats["tabs"] += 1
                i = end + 1
                continue

        if "<details>" in ln:
            ln = ln.replace("<details>", '<details markdown="1">')
            stats["details"] += 1

        def file_sub(mm):
            a = attrs(mm.group(1))
            src = unescape(a.get("src", ""))
            cap = a.get("caption", "").strip()
            name = Path(src).name
            label = cap or name
            target = (srcdir / src).resolve() if src else None
            if src and not src.startswith(("http://", "https://")) and target and target.is_file():
                stats["file_ok"] += 1
                return "[:material-download: %s](%s)" % (label, quote(src, safe="/.:"))
            if src.startswith(("http://", "https://")):
                stats["file_ok"] += 1
                return "[%s](%s)" % (label, src)
            stats["file_missing"] += 1
            return label

        def embed_sub(mm):
            a = attrs(mm.group(1))
            url = a.get("url", "")
            if not url:
                return mm.group(0)
            stats["embed"] += 1
            return "[%s](%s)" % (url, url)

        ln = TYPES_LINK.sub(lambda mm: types_sub(mm, srcdir, stats), ln)
        ln = FILE_TAG.sub(file_sub, ln)
        ln = EMBED_TAG.sub(embed_sub, ln)
        # mkdocs はドットで始まるディレクトリを出力しないため、改名先に向ける
        ln = ln.replace(".gitbook/assets/", ASSETS_DIR + "/")
        out.append(ln)
        i += 1
    return out


def convert_text(text, srcdir, stats):
    lines = text.split("\n")
    res = convert(lines, srcdir, stats)
    return "\n".join(res)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    stats = dict.fromkeys(
        ["hint", "tabs", "tab", "code", "details", "embed", "file_ok", "file_missing", "types_link", "pages"], 0)
    srcs = [ROOT / f for f in TOP_FILES if (ROOT / f).is_file()]
    for sec in SECTIONS:
        srcs += sorted((ROOT / sec).rglob("*.md"))
    for src in srcs:
        rel = src.relative_to(ROOT)
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(convert_text(src.read_text(encoding="utf-8"), src.parent, stats), encoding="utf-8")
        stats["pages"] += 1
    # md 以外(画像など)も同じ相対位置にコピー
    for sec in SECTIONS:
        for f in (ROOT / sec).rglob("*"):
            if f.is_file() and f.suffix != ".md":
                d = OUT / f.relative_to(ROOT)
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, d)
    assets = ROOT / ".gitbook" / "assets"
    if assets.is_dir():
        shutil.copytree(assets, OUT / ASSETS_DIR)
    # 変換されずに残った記法の報告
    left = 0
    for f in OUT.rglob("*.md"):
        txt = f.read_text(encoding="utf-8")
        fl = fence_flags(txt.split("\n"))
        for ln, inf in zip(txt.split("\n"), fl):
            if not inf and re.search(r"\{%.*?%\}", ln):
                left += 1
                print("未変換の記法: %s: %s" % (f.relative_to(OUT), ln.strip()), file=sys.stderr)
    print("prepare_docs: %s (未変換 %d)" % (stats, left))


# ---- nav ----
LINK_RE = re.compile(r"^(\s*)\* \[(.*)\]\(([^)]*)\)\s*$")


def resolve(path):
    """SUMMARY のパスを実在するファイルに解決する(types/ は binexp/ の旧名)。"""
    cands = [path]
    if path.startswith("types/"):
        cands.append("binexp/" + path[len("types/"):])
    for c in cands:
        if c.split("/")[0] in SECTIONS + ["README.md"] and (ROOT / c).is_file():
            return c
    return None


def make_nav():
    items = []  # (level, title, path)
    top = []
    section = None
    sections = []
    for ln in (ROOT / "SUMMARY.md").read_text(encoding="utf-8").split("\n"):
        h = re.match(r"^## (.*?)\s*(<a .*)?$", ln)
        if h:
            section = (unescape(h.group(1)), [])
            sections.append(section)
            continue
        m = LINK_RE.match(ln)
        if not m:
            continue
        level = len(m.group(1)) // 2
        ent = (level, unescape(m.group(2)), m.group(3))
        (section[1] if section else top).append(ent)

    def tree(ents):
        roots, stack = [], []
        for level, title, path in ents:
            node = {"title": title, "path": resolve(path), "children": []}
            while stack and stack[-1][0] >= level:
                stack.pop()
            (stack[-1][1]["children"] if stack else roots).append(node)
            stack.append((level, node))
        return roots

    def prune(nodes):
        res = []
        for n in nodes:
            n["children"] = prune(n["children"])
            if n["path"] or n["children"]:
                res.append(n)
        return res

    def render(nodes, ind):
        lines = []
        for n in nodes:
            pad = " " * ind
            t = json.dumps(n["title"], ensure_ascii=False)
            if n["children"]:
                lines.append("%s- %s:" % (pad, t))
                if n["path"]:
                    lines.append("%s    - %s" % (pad, n["path"]))
                lines.extend(render(n["children"], ind + 4))
            else:
                lines.append("%s- %s: %s" % (pad, t, n["path"]))
        return lines

    lines = []
    lines += render(prune(tree(top)), 2)
    for title, ents in sections:
        sub = prune(tree(ents))
        if sub:
            lines.append("  - %s:" % json.dumps(title, ensure_ascii=False))
            lines += render(sub, 4)
    if (ROOT / "GLOSSARY.md").is_file():
        lines.append('  - "用語集": GLOSSARY.md')
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nav", action="store_true")
    a = ap.parse_args()
    if a.nav:
        print(make_nav())
    else:
        build()
