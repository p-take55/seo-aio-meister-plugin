#!/usr/bin/env python3
"""DataForSEO から、検索数と推移、または検索結果と AI による概要の引用元を取る。

環境変数:
  DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD   API のログインとパスワード（管理画面の API Access）

使い方:
  dataforseo.py balance                         # 残高を見る（無料）
  dataforseo.py volume 語1 語2 ...              # 検索数と推移。1 回 1,000 語まで、何語でも同じ料金
  dataforseo.py volume --file words.txt
  dataforseo.py serp "問い" --own example.com   # 検索結果と AI による概要の引用元。1 問ごとに料金

  --sandbox を付けると、試験用の場所を呼ぶ。料金はかからず、形だけ本物と同じ見本のデータが返る。

出力はタブ区切り。使った料金（ドル）は # で始まる行に出る。
依存は Python 標準ライブラリだけ。仕様: https://docs.dataforseo.com/v3/
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
import re
import urllib.parse

OK = 20000


def fail(message, code=1):
    print(f"dataforseo: {message}", file=sys.stderr)
    sys.exit(code)


def call(host, path, body=None):
    login = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not login or not password:
        fail("DATAFORSEO_LOGIN と DATAFORSEO_PASSWORD が設定されていません")
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    request = urllib.request.Request(
        f"https://{host}/v3/{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        hints = {401: "ログインかパスワードが違う", 402: "残高不足",
                 403: "アカウントの確認（メールや電話番号）が済んでいない、または利用が止められている",
                 429: "呼び出しが多すぎる"}
        detail = error.read().decode(errors="replace")[:400]
        fail(f"HTTP {error.code} {hints.get(error.code, '')} {path}\n{detail}")
    except urllib.error.URLError as error:
        fail(f"接続できません: {error.reason}")
    if payload.get("status_code") != OK:
        fail(f"{path}: {payload.get('status_code')} {payload.get('status_message')}")
    task = (payload.get("tasks") or [{}])[0]
    if task.get("status_code") != OK:
        fail(f"{path}: {task.get('status_code')} {task.get('status_message')}")
    return payload, task


def cell(value):
    return "" if value is None else str(value)


def average(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def cmd_balance(args, host):
    _, task = call(host, "appendix/user_data")
    money = (task.get("result") or [{}])[0].get("money") or {}
    print(f"balance\t{cell(money.get('balance'))}\ntotal_deposited\t{cell(money.get('total'))}")


def cmd_volume(args, host):
    keywords = list(args.keywords)
    if args.file:
        with open(args.file, encoding="utf-8") as handle:
            keywords += [line.strip() for line in handle if line.strip()]
    if not keywords:
        fail("語を 1 つ以上渡してください")
    # 仕様の上限: 1 語 80 文字まで、空白区切りで 10 語まで、1 回 1,000 語まで
    clean = filter_keywords(keywords)
    usable = [k for k in clean if len(k) <= 80 and len(k.split()) <= 10]
    for skipped in sorted(set(clean) - set(usable)):
        print(f"# 上限を超えるので送らない: {skipped}", file=sys.stderr)
    if len(usable) > 1000:
        fail("1 回に送れるのは 1,000 語までです。分けてください")
    if not usable:
        fail("送れる語がありません")
    payload, task = call(host, "keywords_data/google_ads/search_volume/live", [{
        "keywords": usable,
        "location_code": args.location,
        "language_code": args.language,
    }])
    print(f"# cost_usd={payload.get('cost')} location={args.location} language={args.language}")
    print("keyword\tvolume\trecent3_avg\ttrend\tcompetition\tcompetition_index"
          "\tcpc_usd\tbid_low_usd\tbid_high_usd" + ("\tmonthly" if getattr(args, "monthly", False) else ""))
    for item in task.get("result") or []:
        monthly = sorted(item.get("monthly_searches") or [],
                         key=lambda m: (m.get("year") or 0, m.get("month") or 0))
        yearly = average([m.get("search_volume") for m in monthly])
        recent = average([m.get("search_volume") for m in monthly[-3:]])
        trend = f"{recent / yearly:.2f}" if yearly and recent is not None else ""
        row = [
            cell(item.get("keyword")), cell(item.get("search_volume")),
            "" if recent is None else f"{recent:.0f}", trend, cell(item.get("competition")),
            cell(item.get("competition_index")), cell(item.get("cpc")),
            cell(item.get("low_top_of_page_bid")), cell(item.get("high_top_of_page_bid")),
        ]
        if getattr(args, "monthly", False):
            row.append(",".join(f"{m['year']:04d}-{m['month']:02d}:{cell(m.get('search_volume'))}"
                                for m in monthly if isinstance(m.get("year"), int)
                                and isinstance(m.get("month"), int)))
        print("\t".join(row))


def references_in(node, found):
    """AI による概要の中の、引用元（ai_overview_reference）をすべて集める。"""
    if isinstance(node, list):
        for child in node:
            references_in(child, found)
    elif isinstance(node, dict):
        if node.get("type") == "ai_overview_reference" and node.get("url"):
            if node["url"] not in [ref["url"] for ref in found]:
                found.append(node)
        for value in node.values():
            if isinstance(value, (list, dict)):
                references_in(value, found)
    return found


def normalize_host(value):
    value = (value or "").strip()
    try:
        host = (urllib.parse.urlsplit(value if "://" in value else "//" + value).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def target_url(url):
    """Google の転送 URL が包んでいる参照先を取り出す。"""
    for _ in range(5):
        parts = urllib.parse.urlsplit(url or "")
        host = (parts.hostname or "").lower()
        labels = host.split(".")
        google = (len(labels) >= 2 and
                  ((labels[-2] == "google") or
                   (len(labels) >= 3 and labels[-3] == "google" and labels[-2] in ("co", "com") and len(labels[-1]) == 2)))
        if not google or parts.path not in ("/goto", "/url"):
            break
        query = urllib.parse.parse_qs(parts.query)
        target = (query.get("url") or query.get("q") or [""])[0]
        if not target.startswith(("http://", "https://")) or target == url:
            break
        url = target
    return url


UNKNOWN_DOMAIN = "不明"
HOST_IN_TEXT = re.compile(r"(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.IGNORECASE)


def is_google_host(host):
    labels = (host or "").lower().split(".")
    return (len(labels) >= 2 and
            (labels[-2] == "google" or
             (len(labels) >= 3 and labels[-3] == "google" and labels[-2] in ("co", "com") and len(labels[-1]) == 2)))


def result_domain(item):
    """結果 1 件の参照先のドメイン。Google の転送 URL で参照先が読めないときは「不明」。"""
    url = item.get("url") or ""
    target = target_url(url)
    if target != url:
        return urllib.parse.urlsplit(target).hostname or UNKNOWN_DOMAIN
    parts = urllib.parse.urlsplit(url)
    if is_google_host(parts.hostname) and parts.path in ("/goto", "/url"):
        # 転送先が読めない形。表示用の URL（breadcrumb）などから拾えれば使う
        for key in ("breadcrumb", "website_name", "source"):
            found = HOST_IN_TEXT.search(str(item.get(key) or ""))
            if found and not is_google_host(found.group(1)):
                return found.group(1).lower()
        return UNKNOWN_DOMAIN
    return item.get("domain") or parts.hostname or UNKNOWN_DOMAIN


def is_own(domain, own):
    domain, own = normalize_host(domain), normalize_host(own)
    return bool(own) and (domain == own or domain.endswith("." + own))


def filter_keywords(keywords):
    forbidden = set(",!@%^()={};~`<>?\\|―")
    clean = []
    for keyword in keywords:
        if any(c in forbidden or not c.isprintable() for c in keyword):
            print(f"# 記号を含むので送らない: {keyword}", file=sys.stderr)
        else:
            clean.append(keyword)
    return clean


def overview_text(overviews):
    parts = []

    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            for key, value in node.items():
                if key in ("text", "markdown") and isinstance(value, str):
                    parts.append(value)
                elif key == "elements":
                    walk(value)
    for overview in overviews:
        walk(overview.get("elements") or [])
    return "\n".join(parts)[:4000]


def cmd_serp(args, host):
    own = normalize_host(args.own)
    payload, task = call(host, "serp/google/organic/live/advanced", [{
        "keyword": args.question,
        "location_code": args.location,
        "language_code": args.language,
        "device": "desktop",
        "depth": 10,
        "load_async_ai_overview": True,
    }])
    items = ((task.get("result") or [{}])[0].get("items")) or []
    overviews = [item for item in items if item.get("type") == "ai_overview"]
    references = references_in(overviews, [])
    organic = [item for item in items if item.get("type") == "organic"]
    asked = [element.get("title") for item in items if item.get("type") == "people_also_ask"
             for element in (item.get("items") or []) if element.get("title")]

    own_rank = next((cell(o.get("rank_group")) for o in organic if is_own(result_domain(o), own)), "")
    own_cited = any(is_own(result_domain(ref), own) for ref in references)
    unknown_refs = sum(1 for ref in references if result_domain(ref) == UNKNOWN_DOMAIN)
    unknown_organic = sum(1 for o in organic if result_domain(o) == UNKNOWN_DOMAIN)
    print(f"# cost_usd={payload.get('cost')} question={args.question}")
    print(f"ai_overview\t{'あり' if overviews else 'なし'}")
    print(f"references\t{len(references)}")
    print(f"references_unknown\t{unknown_refs}")
    if own:
        # 参照先が読めない行があるときは、「いいえ」と言い切らない
        cited = "はい" if own_cited else ("分からない" if unknown_refs else "いいえ")
        rank = own_rank or ("分からない" if unknown_organic else "10 位以内に無い")
        print(f"own_cited\t{cited}")
        print(f"own_organic_rank\t{rank}")
    print("\nkind\trank\tdomain\turl\ttitle")
    for index, ref in enumerate(references, 1):
        print("\t".join(["引用", str(index), cell(result_domain(ref)), cell(ref.get("url")),
                         cell(ref.get("title") or ref.get("source"))]))
    for item in organic:
        print("\t".join(["検索", cell(item.get("rank_group")), cell(result_domain(item)),
                         cell(item.get("url")), cell(item.get("title"))]))
    for question in asked:
        print(f"質問\t\t\t\t{question}")
    if getattr(args, "text", False):
        print("\n# ai_overview_text")
        print(overview_text(overviews) or "（AI による概要が出ていないので、本文は無い）")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sandbox", action="store_true", help="試験用の場所を呼ぶ（無料、見本のデータ）")
    parser.add_argument("--location", type=int, default=2392, help="国の番号（既定 2392 = 日本）")
    parser.add_argument("--language", default="ja", help="言語（既定 ja）")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("balance", help="残高を見る")
    volume = commands.add_parser("volume", help="検索数と推移")
    volume.add_argument("--monthly", action="store_true", help="月別の検索数も出す")
    volume.add_argument("keywords", nargs="*")
    volume.add_argument("--file", help="1 行 1 語のファイル")
    serp = commands.add_parser("serp", help="検索結果と AI による概要の引用元")
    serp.add_argument("--text", action="store_true", help="AI による概要の本文も出す（最大 4000 文字）")
    serp.add_argument("question")
    serp.add_argument("--own", help="自社のドメイン。引用と順位に自社があるかを出す")
    args = parser.parse_args()
    host = "sandbox.dataforseo.com" if args.sandbox else "api.dataforseo.com"
    {"balance": cmd_balance, "volume": cmd_volume, "serp": cmd_serp}[args.command](args, host)


if __name__ == "__main__":
    main()
