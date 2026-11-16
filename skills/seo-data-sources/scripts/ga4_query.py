#!/usr/bin/env python3
"""Google アナリティクス 4 から、記事に来た人の数と、その後の行動を取る。

環境変数:
  GOOGLE_SERVICE_ACCOUNT_JSON  サービスアカウントの鍵（JSON そのまま、または base64）
  GA4_PROPERTY_ID              プロパティ ID（数字だけ。例 123456789）

使い方:
  ga4_query.py                      # 検索から来た訪問を、最初に開いたページごとに
  ga4_query.py --page /blog/        # URL に /blog/ を含むページだけ
  ga4_query.py --channel all        # 検索に限らず、すべての経路
  ga4_query.py --ai                 # AI のサービスから来た訪問を、来た元とページごとに

出力はタブ区切り。
  通常:  landing_page, sessions, prev_sessions, engaged_sessions, key_events
  --ai:  source, landing_page, sessions, prev_sessions, engaged_sessions, key_events
prev_sessions は、同じ長さの 1 つ前の期間の訪問数。key_events は、GA4 で重要と設定した行動の回数。

同じフォルダの google_auth.py を使う。
"""
import argparse
import datetime
import os

from google_auth import access_token, api_post, fail

SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
LAG_DAYS = 2  # GA4 の数字は 1〜2 日遅れて確定する
# AI のサービスから来た訪問を見分ける、来た元の名前（部分一致の正規表現）
AI_SOURCES = (r"chatgpt\.com|chat\.openai\.com|perplexity|claude\.ai|gemini\.google\.com"
              r"|copilot\.microsoft\.com|copilot\.com|deepseek|grok\.com|felo\.ai|genspark")


def string_filter(field, value, match_type):
    return {"filter": {"fieldName": field,
                       "stringFilter": {"value": value, "matchType": match_type}}}


def build_body(start, end, ai, channel, page, limit):
    dimensions = (["sessionSource"] if ai else []) + ["landingPagePlusQueryString"]
    filters = []
    if ai:
        filters.append(string_filter("sessionSource", AI_SOURCES, "PARTIAL_REGEXP"))
    elif channel and channel != "all":
        filters.append(string_filter("sessionDefaultChannelGroup", channel, "EXACT"))
    if page:
        filters.append(string_filter("landingPagePlusQueryString", page, "CONTAINS"))
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": name} for name in dimensions],
        "metrics": [{"name": "sessions"}, {"name": "engagedSessions"}, {"name": "keyEvents"}],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        "limit": str(limit),
    }
    if len(filters) == 1:
        body["dimensionFilter"] = filters[0]
    elif filters:
        body["dimensionFilter"] = {"andGroup": {"expressions": filters}}
    return body


def rows_of(response):
    for row in response.get("rows", []):
        keys = tuple(value.get("value", "") for value in row.get("dimensionValues", []))
        metrics = [value.get("value", "0") for value in row.get("metricValues", [])]
        yield keys, metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=28, help="集計する日数（既定 28）")
    parser.add_argument("--channel", default="Organic Search",
                        help="経路。既定は Organic Search。all ですべて")
    parser.add_argument("--ai", action="store_true", help="AI のサービスから来た訪問を見る")
    parser.add_argument("--page", help="URL にこの文字列を含むページだけにする")
    parser.add_argument("--limit", type=int, default=200, help="行数の上限（既定 200）")
    args = parser.parse_args()

    property_id = os.environ.get("GA4_PROPERTY_ID", "").strip().removeprefix("properties/")
    if not property_id.isdigit():
        fail("GA4_PROPERTY_ID が設定されていないか、数字ではありません")
    token = access_token(SCOPE)
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"

    end = datetime.date.today() - datetime.timedelta(days=LAG_DAYS)
    start = end - datetime.timedelta(days=args.days - 1)
    prev_end = start - datetime.timedelta(days=1)
    prev_start = prev_end - datetime.timedelta(days=args.days - 1)

    current = api_post(url, token, build_body(start, end, args.ai, args.channel, args.page, args.limit))
    previous = api_post(url, token,
                        build_body(prev_start, prev_end, args.ai, args.channel, args.page, 10000))
    prev = {keys: metrics[0] for keys, metrics in rows_of(previous)}

    scope = "AI のサービス" if args.ai else args.channel
    print(f"# property={property_id} 経路={scope} period={start}..{end} prev={prev_start}..{prev_end}")
    head = (["source"] if args.ai else []) + ["landing_page"]
    print("\t".join(head + ["sessions", "prev_sessions", "engaged_sessions", "key_events"]))
    for keys, metrics in rows_of(current):
        print("\t".join(list(keys) + [metrics[0], prev.get(keys, "0"), metrics[1], metrics[2]]))


if __name__ == "__main__":
    main()
