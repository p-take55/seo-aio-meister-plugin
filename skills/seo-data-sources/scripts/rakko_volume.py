#!/usr/bin/env python3
"""ラッコキーワード API で、キーワードの月間検索数と増減率をまとめて取る。

環境変数:
  RAKKO_API_KEY  ラッコキーワードの API キー（スタンダードプラン以上）

使い方:
  rakko_volume.py 語1 語2 ...          # 登録して、完了を待ち、結果を出す
  rakko_volume.py --file words.txt     # 1 行 1 語のファイルから
  rakko_volume.py --request-id 12345   # 登録済みの調査の結果だけ取り直す（クレジットを使わない）

出力はタブ区切り: keyword, volume, change_3m, change_12m, competition, source
change_3m / change_12m は、直近月が 3 か月・12 か月の平均からどれだけ増減したかの比率（0.3 = +30%）。

1 回の登録で最低 15 クレジットを使う。候補はまとめて 1 回で送る。
依存は Python 標準ライブラリだけ。仕様: https://api.rakkokeyword.com/docs
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import urllib.parse

BASE = "https://api.rakkokeyword.com"


def fail(message, code=1):
    print(f"rakko_volume: {message}", file=sys.stderr)
    sys.exit(code)


def api_base():
    value = os.environ.get("RAKKO_API_BASE_FOR_TEST")
    if value is None:
        return BASE
    try:
        parts = urllib.parse.urlsplit(value)
        valid = (parts.scheme in ("http", "https") and parts.hostname in ("localhost", "127.0.0.1")
                 and not parts.username and not parts.password and not parts.query and not parts.fragment)
        parts.port
    except ValueError:
        valid = False
    if not valid:
        fail("RAKKO_API_BASE_FOR_TEST は localhost / 127.0.0.1 の URL だけ指定できます")
    return value.rstrip("/")


def unexpected(payload):
    keys = ", ".join(map(str, payload.keys())) if isinstance(payload, dict) else "なし"
    fail(f"応答の形式が想定と違います（最上位のキー: {keys}）")


def result_data(payload, kind):
    try:
        data = payload["data"]
        if not isinstance(data, dict):
            raise TypeError
        if kind == "registration":
            if not isinstance(data["requestId"], int) or not isinstance(payload["meta"], dict):
                raise TypeError
            payload["meta"]["consumedCredit"]
        elif kind == "status":
            if type(data["isCompleted"]) is not bool:
                raise TypeError
        elif kind == "results":
            data["query"]["location"], data["query"]["language"], data["summary"]["returnedCount"]
            if not isinstance(data["items"], list):
                raise TypeError
            for item in data["items"]:
                if not isinstance(item, dict) or not isinstance(item["keyword"], str):
                    raise TypeError
                for key in ("metrics", "trends"):
                    if item.get(key) is not None and not isinstance(item[key], dict):
                        raise TypeError
                change = (item.get("trends") or {}).get("changeRate")
                if change is not None and not isinstance(change, dict):
                    raise TypeError
        return data
    except (KeyError, TypeError, IndexError):
        unexpected(payload)


def call(method, path, body=None):
    request = urllib.request.Request(
        api_base() + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"X-API-Key": os.environ["RAKKO_API_KEY"], "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        hints = {402: "クレジット不足", 403: "API キーが無効、またはプランが対象外", 429: "レート制限（60 回 / 60 秒）"}
        detail = error.read().decode(errors="replace")[:500]
        fail(f"HTTP {error.code} {hints.get(error.code, '')} {method} {path}\n{detail}")
    except urllib.error.URLError as error:
        fail(f"接続できません: {error.reason}")
    if not isinstance(payload, dict) or "result" not in payload:
        unexpected(payload)
    if not payload.get("result"):
        fail(f"{method} {path} が失敗: {payload.get('errors')}")
    return payload


def cell(value):
    return "" if value is None else str(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("keywords", nargs="*", help="調べる語")
    parser.add_argument("--file", help="1 行 1 語のファイル")
    parser.add_argument("--request-id", type=int, help="登録済みの調査の結果を取る")
    parser.add_argument("--location", default="Japan")
    parser.add_argument("--language", default="Japanese")
    parser.add_argument("--timeout", type=int, default=300, help="完了を待つ秒数（既定 300）")
    args = parser.parse_args()

    api_base()
    if not os.environ.get("RAKKO_API_KEY"):
        fail("RAKKO_API_KEY が設定されていません")

    request_id = args.request_id
    if request_id is None:
        keywords = list(args.keywords)
        if args.file:
            with open(args.file, encoding="utf-8") as handle:
                keywords += [line.strip() for line in handle if line.strip()]
        if not keywords:
            fail("語を 1 つ以上渡してください")
        registered = call("POST", "/v1/search-volume", {
            "keywords": keywords,
            "location": args.location,
            "language": args.language,
        })
        request_id = result_data(registered, "registration")["requestId"]
        print(f"# requestId={request_id} consumedCredit={registered['meta']['consumedCredit']}",
              file=sys.stderr)

    deadline = time.time() + args.timeout
    wait = 10
    while True:
        status = result_data(call("GET", f"/v1/search-volume/{request_id}/status"), "status")
        if status.get("isCompleted"):
            break
        if time.time() + wait > deadline:
            fail(f"まだ完了していません。後で --request-id {request_id} で取り直してください"
                 "（取り直しはクレジットを使いません）", code=2)
        time.sleep(wait)
        wait = 15

    payload = call("POST", f"/v1/search-volume/{request_id}/results",
                   {"noiseReduction": False, "limit": 50000})
    data = result_data(payload, "results")
    print(f"# requestId={request_id} location={data['query']['location']} "
          f"language={data['query']['language']} rows={data['summary']['returnedCount']}")
    print("keyword\tvolume\tchange_3m\tchange_12m\tcompetition\tsource")
    for item in data["items"]:
        metrics = item.get("metrics") or {}
        change = (item.get("trends") or {}).get("changeRate") or {}
        print("\t".join([
            item["keyword"], cell(metrics.get("searchVolume")), cell(change.get("3m")),
            cell(change.get("12m")), cell(metrics.get("competition")), cell(item.get("dataSource")),
        ]))


if __name__ == "__main__":
    main()
