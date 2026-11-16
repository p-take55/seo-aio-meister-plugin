#!/usr/bin/env python3
"""Search Console から、自社サイトが表示された検索語の実数を取る。

環境変数:
  GOOGLE_SERVICE_ACCOUNT_JSON  サービスアカウントの鍵（JSON そのまま、または base64）
  GSC_SITE_URL              プロパティ。例 sc-domain:example.com / https://example.com/

出力はタブ区切り: query（または page）, clicks, impressions, prev_impressions, position
prev_impressions は、同じ長さの 1 つ前の期間の表示回数。

  --by page          検索語ではなく、ページごとに集計する
  --by date          日ごとの推移を出す（出力は date, clicks, impressions, position。データの無い日は 0）
  --by total         サイト全体の合計を、今の期間と 1 つ前の期間で出す（匿名化された検索も含む）
  --page 〈文字列〉   URL にこの文字列を含むページだけを対象にする

同じフォルダの google_auth.py を使う。
"""
import argparse
import datetime
import os
import urllib.parse

from google_auth import access_token, api_post, fail

SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
LAG_DAYS = 3  # Search Console の数字は 2〜3 日遅れて確定する


def build_body(start, end, by, contains, page, limit):
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": [] if by == "total" else [by],
        "rowLimit": limit,
    }
    filters = []
    if contains:
        filters.append({"dimension": "query", "operator": "contains", "expression": contains})
    if page:
        filters.append({"dimension": "page", "operator": "contains", "expression": page})
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]
    return body


def query(token, site_url, body):
    url = ("https://www.googleapis.com/webmasters/v3/sites/"
           + urllib.parse.quote(site_url, safe="") + "/searchAnalytics/query")
    return api_post(url, token, body).get("rows", [])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=28, help="集計する日数（既定 28）")
    parser.add_argument("--by", choices=["query", "page", "date", "total"], default="query",
                        help="集計の単位（既定 query）")
    parser.add_argument("--contains", help="この文字列を含む検索語だけにする")
    parser.add_argument("--page", help="URL にこの文字列を含むページだけにする")
    parser.add_argument("--limit", type=int, default=500, help="行数の上限（既定 500、最大 25000）")
    args = parser.parse_args()

    site_url = os.environ.get("GSC_SITE_URL", "").strip()
    if not site_url:
        fail("GSC_SITE_URL が設定されていません")
    token = access_token(SCOPE)

    end = datetime.date.today() - datetime.timedelta(days=LAG_DAYS)
    start = end - datetime.timedelta(days=args.days - 1)
    prev_end = start - datetime.timedelta(days=1)
    prev_start = prev_end - datetime.timedelta(days=args.days - 1)

    header = f"# site={site_url} period={start}..{end} prev={prev_start}..{prev_end}"

    if args.by == "date":
        found = {
            row["keys"][0]: row
            for row in query(token, site_url,
                             build_body(start, end, "date", args.contains, args.page, 25000))
        }
        print(f"# site={site_url} period={start}..{end}")
        print("date\tclicks\timpressions\tposition")
        day = start
        while day <= end:
            row = found.get(day.isoformat())
            if row:
                print(f"{day}\t{row['clicks']:.0f}\t{row['impressions']:.0f}\t{row['position']:.1f}")
            else:
                print(f"{day}\t0\t0\t")
            day += datetime.timedelta(days=1)
        return

    if args.by == "total":
        print(header)
        print("period\tclicks\timpressions\tposition")
        for label, first, last in (("current", start, end), ("prev", prev_start, prev_end)):
            rows = query(token, site_url,
                         build_body(first, last, "total", args.contains, args.page, 1))
            if rows:
                row = rows[0]
                print(f"{label}\t{row['clicks']:.0f}\t{row['impressions']:.0f}\t{row['position']:.1f}")
            else:
                print(f"{label}\t0\t0\t")
        return

    rows = query(token, site_url,
                 build_body(start, end, args.by, args.contains, args.page, args.limit))
    prev = {
        row["keys"][0]: row["impressions"]
        for row in query(token, site_url,
                         build_body(prev_start, prev_end, args.by, args.contains, args.page, 25000))
    }

    print(header)
    print(f"{args.by}\tclicks\timpressions\tprev_impressions\tposition")
    for row in rows:
        term = row["keys"][0]
        print(f"{term}\t{row['clicks']:.0f}\t{row['impressions']:.0f}"
              f"\t{prev.get(term, 0):.0f}\t{row['position']:.1f}")


if __name__ == "__main__":
    main()
