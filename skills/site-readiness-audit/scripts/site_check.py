#!/usr/bin/env python3
"""サイトが検索と AI に読まれる状態かを、外から機械的に確かめる。

使い方:
  site_check.py https://example.com
  site_check.py https://example.com --prefer /blog/ --pages 8

確かめること:
  1. robots.txt が、検索と AI のクローラーを許可しているか
  2. クローラーの名乗りでアクセスしたとき、サーバーが拒否しないか
  3. サイトマップがあり、ページが載っているか
  4. ページごとの題名・説明・正規 URL・noindex・構造化データ・著者・日付・本文の量

サイトへのアクセスは、robots.txt、サイトマップ、トップページ、指定した数のページだけ。
依存は Python 標準ライブラリだけ。
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
import zlib
from html.parser import HTMLParser

BROWSER_UA = "Mozilla/5.0 (compatible; site-readiness-check/1.0)"

# (robots.txt での名前, 役割, アクセス時の名乗り)
CRAWLERS = [
    ("Googlebot", "Google 検索と AI による概要",
     "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    ("Bingbot", "Bing 検索と Copilot",
     "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"),
    ("OAI-SearchBot", "ChatGPT の検索",
     "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)"),
    ("ChatGPT-User", "ChatGPT が利用者の求めで開く",
     "Mozilla/5.0 (compatible; ChatGPT-User/1.0; +https://openai.com/bot)"),
    ("GPTBot", "OpenAI の学習",
     "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)"),
    ("Claude-SearchBot", "Claude の検索",
     "Mozilla/5.0 (compatible; Claude-SearchBot/1.0; +https://www.anthropic.com)"),
    ("Claude-User", "Claude が利用者の求めで開く",
     "Mozilla/5.0 (compatible; Claude-User/1.0; +https://www.anthropic.com)"),
    ("ClaudeBot", "Anthropic の学習",
     "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)"),
    ("PerplexityBot", "Perplexity の検索",
     "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)"),
    ("Perplexity-User", "Perplexity が利用者の求めで開く",
     "Mozilla/5.0 (compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)"),
    ("Google-Extended", "Gemini の学習（検索には影響しない）", None),
    ("Applebot-Extended", "Apple の学習", None),
    ("CCBot", "Common Crawl（多くの AI が学習に使う）", None),
]


def fetch(url, user_agent=BROWSER_UA, limit=3_000_000):
    """(status, final_url, headers, body) を返す。接続できなければ status は None。"""
    request = urllib.request.Request(url, headers={
        "User-Agent": user_agent, "Accept": "*/*", "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read(limit)
            if response.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                # 途中までしか読んでいない圧縮データも展開できるよう、逐次で解く
                try:
                    body = zlib.decompressobj(zlib.MAX_WBITS | 16).decompress(body)
                except zlib.error:
                    pass
            return response.status, response.geturl(), response.headers, body
    except urllib.error.HTTPError as error:
        return error.code, url, error.headers, b""
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return None, url, {}, str(error).encode()


def decode(body, headers):
    content_type = headers.get("Content-Type", "")
    match = re.search(r"charset\s*=\s*[\"']?([^\s;\"']+)", content_type, re.I)
    charset = match.group(1) if match else None
    if not charset:
        # 属性の順序によらず meta charset と http-equiv の両方を読む。
        class CharsetParser(HTMLParser):
            charset = None

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag != "meta" or self.charset:
                    return
                self.charset = attrs.get("charset")
                if not self.charset and attrs.get("http-equiv", "").lower() == "content-type":
                    found = re.search(r"charset\s*=\s*([^\s;]+)", attrs.get("content", ""), re.I)
                    if found:
                        self.charset = found.group(1).strip("\"'")
        meta = CharsetParser()
        meta.feed(body[:2048].decode("ascii", errors="replace"))
        charset = meta.charset
    try:
        return body.decode(charset or "utf-8", errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def site_host(url):
    host = (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def same_site(url, hosts):
    parsed = urllib.parse.urlsplit(url)
    host = site_host(url)
    return parsed.scheme in ("http", "https") and bool(host) and any(
        host == known or host.endswith("." + known) for known in hosts)


def llms_present(status, headers, body):
    media_type = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    beginning = body.lstrip().lower()
    return (status == 200 and media_type in ("", "text/plain", "text/markdown")
            and not beginning.startswith((b"<!doctype html", b"<html")))


def robots_verdict(robots, name, home, urls):
    blocked = list(dict.fromkeys(
        (urllib.parse.urlsplit(url).path or "/") +
        (("?" + urllib.parse.urlsplit(url).query) if urllib.parse.urlsplit(url).query else "")
        for url in [home] + list(urls) if not robots.can_fetch(name, url)))
    verdict = "拒否" if not robots.can_fetch(name, home) else "一部拒否" if blocked else "許可"
    return verdict + ("（" + ", ".join(blocked) + "）" if blocked else "")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta = {}
        self.canonical = None
        self.lang = None
        self.h1 = 0
        self.jsonld = []
        self.links = []
        self.text_chars = 0
        self._in_head = False
        self._head_closed = False
        self._svg_depth = 0
        self._title_seen = False
        self._stack = []
        self._buffer = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head" and not self._head_closed:
            self._in_head = True
        if tag == "svg":
            self._svg_depth += 1
        if tag == "html":
            self.lang = attrs.get("lang")
        elif tag == "meta":
            key = (attrs.get("name") or attrs.get("property") or "").lower()
            if key:
                self.meta[key] = attrs.get("content") or ""
        elif tag == "link" and "canonical" in (attrs.get("rel") or "").lower():
            self.canonical = attrs.get("href")
        elif tag == "h1":
            self.h1 += 1
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag in ("script", "style", "title", "noscript"):
            self._stack.append(tag)
            is_jsonld = tag == "script" and "ld+json" in (attrs.get("type") or "")
            # 題名は <head> の外に出ることがある（描きながら送るサイト）。図の中の <title> だけを除く。
            is_title = tag == "title" and not self._svg_depth and not self._title_seen
            if is_title:
                self._title_seen = True
            self._buffer = [] if (is_jsonld or is_title) else None

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
            self._head_closed = True
        if tag == "svg":
            self._svg_depth = max(0, self._svg_depth - 1)
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
            if self._buffer is not None:
                text = "".join(self._buffer)
                if tag == "title":
                    self.title = text.strip()
                else:
                    self.jsonld.append(text)
            self._buffer = None

    def handle_data(self, data):
        if self._stack:
            if self._buffer is not None:
                self._buffer.append(data)
            return
        self.text_chars += len(data.strip())


def jsonld_summary(blocks):
    """JSON-LD から、型・著者の有無・公開日・更新日を拾う。"""
    types, has_author, published, modified, broken = [], False, None, None, 0

    def walk(node):
        nonlocal has_author, published, modified
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            kind = node.get("@type")
            if kind:
                types.extend(kind if isinstance(kind, list) else [kind])
            has_author = has_author or bool(node.get("author"))
            published = published or node.get("datePublished")
            modified = modified or node.get("dateModified")
            for value in node.values():
                if isinstance(value, (list, dict)):
                    walk(value)

    for block in blocks:
        try:
            walk(json.loads(block))
        except (json.JSONDecodeError, TypeError):
            broken += 1
    return sorted(set(map(str, types))), has_author, published, modified, broken


def sitemap_urls(url, depth=0):
    """(ページ URL の一覧, 更新日つきの数, 状態) を返す。索引は 1 段だけたどる。"""
    status, _, headers, body = fetch(url)
    if status != 200:
        return [], 0, status
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return [], 0, "XML として読めない"
    strip = lambda tag: tag.rsplit("}", 1)[-1]
    urls, with_lastmod = [], 0
    if strip(root.tag) == "sitemapindex" and depth == 0:
        children = [node for node in root if any(strip(c.tag) == "loc" and c.text for c in node)]
        for node in children[:20]:
            loc = next((c.text for c in node if strip(c.tag) == "loc"), None)
            if loc:
                found, dated, _ = sitemap_urls(loc.strip(), depth + 1)
                urls += found
                with_lastmod += dated
        return urls, with_lastmod, ("200（子サイトマップは最大 20 件。残りを省略）" if len(children) > 20 else status)
    if strip(root.tag) == "sitemapindex":
        return [], 0, "索引の追加階層は省略"
    for node in root:
        loc = next((c.text for c in node if strip(c.tag) == "loc"), None)
        if loc:
            urls.append(loc.strip())
            with_lastmod += any(strip(c.tag) == "lastmod" for c in node)
    return urls, with_lastmod, status


def short(text, width=70):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("site", help="サイトの URL。例 https://example.com")
    parser.add_argument("--pages", type=int, default=6, help="調べるページの数（既定 6）")
    parser.add_argument("--url", action="append", default=[], help="追加で必ず調べる同じサイトの URL（複数指定可）")
    parser.add_argument("--prefer", help="この文字列を含む URL を優先して調べる。例 /blog/")
    args = parser.parse_args()

    parts = urllib.parse.urlsplit(args.site if "://" in args.site else "https://" + args.site)
    base = f"{parts.scheme}://{parts.netloc}"
    home = base + "/"

    home_result = fetch(home)
    baseline, final_home, home_headers, home_body = home_result
    if baseline is None:
        print("トップページを取得できません: " + decode(home_body, home_headers), file=sys.stderr)
        return 2
    hosts = {site_host(home), site_host(final_home)}
    status, _, headers, body = fetch(base + "/robots.txt")
    robots = urllib.robotparser.RobotFileParser()
    robots_text = decode(body, headers) if status == 200 else ""
    robots.parse(robots_text.splitlines())
    declared = re.findall(r"(?im)^\s*sitemap\s*:\s*(\S+)", robots_text)
    candidates = declared or [base + "/sitemap.xml"]
    urls, sitemap_rows = [], []
    for candidate in candidates:
        found, with_lastmod, state = sitemap_urls(candidate)
        sitemap_rows.append(f"{candidate}\t状態 {state}\t{len(found)} ページ\t更新日つき {with_lastmod}")
        urls.extend(found)
    foreign = [url for url in urls if not same_site(url, hosts)]
    urls = [url for url in urls if same_site(url, hosts)]
    discovered_from_links = not urls
    if discovered_from_links and baseline == 200:
        page = PageParser()
        page.feed(decode(home_body, home_headers))
        for href in page.links:
            link = urllib.parse.urldefrag(urllib.parse.urljoin(final_home, href)).url
            if same_site(link, hosts) and link not in urls:
                urls.append(link)
    explicit = []
    for url in args.url:
        url = urllib.parse.urldefrag(urllib.parse.urljoin(final_home, url)).url
        if not same_site(url, hosts):
            print(f"別のホストなので省略: {url}", file=sys.stderr)
        elif url not in explicit:
            explicit.append(url)
    preferred = [url for url in urls if args.prefer and args.prefer in url]
    discovered = list(dict.fromkeys([home] + preferred + urls))
    discovered = [url for url in discovered if url not in explicit]
    targets = explicit + discovered[:max(args.pages, 1)]
    # 転送後のパスも robots.txt の判定に含める。
    results = {url: home_result if url == home else fetch(url) for url in targets}
    robot_urls = targets + [result[1] for result in results.values()]
    if args.prefer:
        robot_urls.append(urllib.parse.urljoin(final_home, args.prefer))

    print(f"# {base}\n\n## 1. robots.txt")
    if status == 200:
        print(f"あり（{len(robots_text.splitlines())} 行）")
    elif status == 404:
        print("なし（すべて許可の扱い）")
    else:
        print(f"取得できない（状態 {status}）。クローラーが全体を読めないおそれがある")
    named = {m.strip().lower() for m in re.findall(r"(?im)^\s*user-agent\s*:\s*(.+)$", robots_text)}
    print("\nクローラー\t役割\trobots.txt\t名指しの規則")
    for name, role, _ in CRAWLERS:
        print(f"{name}\t{role}\t{robots_verdict(robots, name, home, robot_urls)}\t{'あり' if name.lower() in named else 'なし'}")
    if re.search(r"(?im)^\s*(dis)?allow\s*:.*[*$]", robots_text):
        print("注意: 規則に * や $ が含まれる。この判定は単純な前方一致なので、該当する行は目で確かめる")

    print("\n## 2. クローラーの名乗りでトップページを開く")
    print(f"通常のブラウザ\t{baseline}")
    for name, _, agent in CRAWLERS:
        if agent:
            code, _, _, _ = fetch(home, user_agent=agent, limit=2000)
            mark = ("  名乗りだけ拒否（本物が通るかは不明）" if baseline == 200 and code in (401, 403, 429, 503)
                    else "" if code == baseline else "  ← 通常と違う")
            print(f"{name}\t{code}{mark}")
    print("名乗りを変えただけの確認です。CDN は偽の名乗りを止めることがあり、本物のクローラーが通るかはここからは分かりません。")
    print("\n## 3. サイトマップ")
    for row in sitemap_rows:
        print(row)
    if not declared:
        print("robots.txt にサイトマップの記載がない")
    if foreign:
        print(f"注意: 別のドメインの URL が {len(foreign)} 件ある。例 {foreign[0]}")
    code, _, llms_headers, llms_body = fetch(base + "/llms.txt", limit=2000)
    print(f"\n## 4. llms.txt\n{'あり' if llms_present(code, llms_headers, llms_body) else 'なし'}"
          "（任意。主要な AI が読むとは確かめられていない）")
    if discovered_from_links:
        print(f"\nサイトマップにページが無いので、トップページのリンクから {len(urls)} 件を拾った")
    print(f"\n## 5. ページ（{len(targets)} 件）")
    for url in targets:
        status, final, headers, body = results[url]
        print(f"\n### {url}")
        if status != 200:
            print(f"状態\t{status}")
            continue
        page = PageParser()
        page.feed(decode(body, headers))
        types, has_author, published, modified, broken = jsonld_summary(page.jsonld)
        header_robots = headers.get("X-Robots-Tag", "") if hasattr(headers, "get") else ""
        noindex = "noindex" in (page.meta.get("robots", "") + header_robots).lower()
        canonical = urllib.parse.urljoin(final, page.canonical) if page.canonical else None
        rows = [
            ("状態", f"{status}" + (f"（転送先 {final}）" if final.rstrip('/') != url.rstrip('/') else "")),
            ("題名", short(page.title) or "なし"),
            ("説明", short(page.meta.get("description")) or "なし"),
            ("言語", page.lang or "指定なし"),
            ("h1 の数", str(page.h1)),
            ("正規 URL", canonical or "なし"),
            ("noindex", "あり ← 検索に載らない" if noindex else "なし"),
            ("構造化データ", ", ".join(types) or "なし"),
            ("著者", "あり" if has_author or page.meta.get("author") else "なし"),
            ("公開日", str(published or page.meta.get("article:published_time") or "なし")),
            ("更新日", str(modified or page.meta.get("article:modified_time") or "なし")),
            ("本文の文字数", f"{page.text_chars}"
             + ("  ← 少ない。画面を JavaScript で描いているおそれ" if page.text_chars < 300 else "")),
        ]
        if canonical and canonical.rstrip("/") != final.rstrip("/"):
            rows.append(("注意", "正規 URL がこのページ自身ではない"))
        if broken:
            rows.append(("注意", f"読めない構造化データが {broken} 個ある"))
        for key, value in rows:
            print(f"{key}\t{value}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
