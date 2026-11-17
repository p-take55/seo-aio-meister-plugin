#!/usr/bin/env python3
"""記事の原稿（Markdown / MDX）を、ブラウザで読める 1 枚の HTML にする。

公開前の原稿を、ダッシュボードの「記事」から開けるようにするためのもの。
本番のサイトの見た目とは同じにならない。表示は「下書き」と分かるようにする。

使い方:
  python3 article_preview.py 原稿.mdx 出力.html \
      --state in_review --source-url https://github.com/... --checked-on 2026-11-17

対応する書き方: 前付け（title / description / date）、## と ### の見出し、段落、
番号付き・番号なしの一覧、**太字**、[リンク](URL)、`コード`、HTML の塊（表など）。
import / export の行と JSX の部品は表示しない（行数を標準エラーに出す）。
外部のライブラリは使わない。
"""
import argparse
import html
import re
import sys

STATE_LABELS = {
    "brief": "概要あり（原稿なし）",
    "draft": "原稿あり・受け入れ確認の前",
    "in_review": "受け入れ確認中・未公開",
    "published": "公開済み（この画面は原稿の写し）",
}


def parse_front_matter(text):
    meta = {}
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                m = re.match(r'^(\w+):\s*"?(.*?)"?\s*$', line)
                if m:
                    meta[m.group(1)] = m.group(2)
            text = text[end + 4:].lstrip("\n")
    return meta, text


def inline(s):
    out, pos = [], 0
    for m in re.finditer(r"`([^`]+)`", s):
        out.append(inline_text(s[pos:m.start()]))
        out.append("<code>" + html.escape(m.group(1)) + "</code>")
        pos = m.end()
    out.append(inline_text(s[pos:]))
    return "".join(out)


def inline_text(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: '<a href="%s" target="_blank" rel="noopener">%s</a>'
        % (html.escape(html.unescape(m.group(2))), m.group(1)),
        s,
    )
    return s


def to_html(body):
    lines = body.splitlines()
    out, para, skipped = [], [], 0
    i = 0

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush(); i += 1; continue
        if re.match(r"^(import|export)\s", s):
            flush(); skipped += 1; i += 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            flush()
            lv = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lv, inline(m.group(2)), lv))
            i += 1; continue
        if s.startswith("<"):
            flush()
            block = []
            while i < len(lines) and lines[i].strip():
                block.append(lines[i]); i += 1
            if re.match(r"^<[A-Z]", s):  # JSX の部品は出さない
                skipped += len(block); continue
            out.append("\n".join(block)); continue
        lm = re.match(r"^(\d+\.|[-*])\s+(.*)$", s)
        if lm:
            flush()
            tag = "ol" if lm.group(1)[0].isdigit() else "ul"
            items = []
            while i < len(lines):
                t = lines[i].strip()
                mm = re.match(r"^(\d+\.|[-*])\s+(.*)$", t)
                if mm and (mm.group(1)[0].isdigit()) == (tag == "ol"):
                    items.append(mm.group(2))
                elif t and items and lines[i].startswith((" ", "\t")):
                    items[-1] += " " + t
                else:
                    break
                i += 1
            out.append("<%s>%s</%s>" % (tag, "".join("<li>" + inline(x) + "</li>" for x in items), tag))
            continue
        if s.startswith(">"):
            flush()
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip()[1:].strip()); i += 1
            out.append("<blockquote><p>" + inline(" ".join(q)) + "</p></blockquote>")
            continue
        para.append(s); i += 1
    flush()
    return "\n".join(out), skipped


CSS = """
:root{color-scheme:light dark;--fg:#1f2328;--muted:#59636e;--line:#d1d9e0;--bg:#fff;--note:#fff8c5;--noteline:#d4a72c;--link:#0969da}
@media (prefers-color-scheme:dark){:root{--fg:#e6edf3;--muted:#9198a1;--line:#3d444d;--bg:#0d1117;--note:#3b2e00;--noteline:#9e6a03;--link:#4493f8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.85 -apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP",sans-serif}
.bar{position:sticky;top:0;background:var(--note);border-bottom:1px solid var(--noteline);padding:.6rem 1rem;font-size:.85rem;line-height:1.6}
.bar a{color:var(--link)}main{max-width:44rem;margin:0 auto;padding:2rem 1.25rem 5rem}
h1{font-size:1.75rem;line-height:1.4;margin:.5rem 0 1rem}h2{font-size:1.35rem;margin:2.6rem 0 .8rem;padding-bottom:.3rem;border-bottom:1px solid var(--line)}h3{font-size:1.1rem;margin:1.8rem 0 .5rem}
.meta{color:var(--muted);font-size:.85rem}.desc{color:var(--muted);border-left:3px solid var(--line);padding-left:.9rem;margin:1rem 0 2rem}
a{color:var(--link)}table{border-collapse:collapse;width:100%;margin:1.2rem 0;font-size:.9rem;display:block;overflow-x:auto}th,td{border:1px solid var(--line);padding:.45rem .6rem;text-align:left;vertical-align:top}th{background:color-mix(in srgb,var(--line) 35%,transparent)}
code{font-size:.9em;background:color-mix(in srgb,var(--line) 40%,transparent);padding:.1em .3em;border-radius:4px}li{margin:.3rem 0}blockquote{margin:1rem 0;padding-left:1rem;border-left:3px solid var(--line);color:var(--muted)}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--state", default="draft", choices=list(STATE_LABELS))
    ap.add_argument("--source-url", help="原稿の置き場所（作業ブランチのファイルなど）")
    ap.add_argument("--checked-on", help="原稿を写した日")
    ap.add_argument("--back", default="seo-dashboard.html#articles", help="戻り先")
    a = ap.parse_args()

    meta, body = parse_front_matter(open(a.src, encoding="utf-8").read())
    content, skipped = to_html(body)
    title = meta.get("title", "（題なし）")
    bar = ["<strong>プレビュー</strong>: " + STATE_LABELS[a.state] + "。本番のサイトの見た目とは違います。"]
    if a.source_url:
        bar.append('原稿: <a href="%s" target="_blank" rel="noopener">置き場所</a>' % html.escape(a.source_url))
    if a.checked_on:
        bar.append("写した日 " + html.escape(a.checked_on))
    bar.append('<a href="%s">ダッシュボードへ戻る</a>' % html.escape(a.back))
    meta_line = []
    if meta.get("date"):
        meta_line.append("日付（前付け）: " + html.escape(meta["date"]))
    meta_line.append("著者: " + html.escape(meta.get("authorName", "未設定")))
    doc = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>[プレビュー] %s</title><style>%s</style></head>
<body><div class="bar">%s</div><main><article>
<p class="meta">%s</p><h1>%s</h1>%s
%s
</article></main></body></html>
""" % (
        html.escape(title), CSS, " · ".join(bar), " · ".join(meta_line), html.escape(title),
        ('<p class="desc">' + html.escape(meta["description"]) + "</p>") if meta.get("description") else "",
        content,
    )
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(doc)
    if skipped:
        print("表示しなかった行（import / export / JSX）: %d" % skipped, file=sys.stderr)
    print("OK " + a.out)


if __name__ == "__main__":
    main()
