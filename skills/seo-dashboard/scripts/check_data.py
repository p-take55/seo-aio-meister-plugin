#!/usr/bin/env python3
"""SEO/AIO dashboard JSON validator (Python 3 standard library only)."""
import datetime
import json
import math
import re
import sys


def array(spec):
    return ("array", spec)


def enum(*values):
    return ("enum", values)


def nullable(spec):
    return ("nullable", spec)


PERIOD = {"start": "date", "end": "date"}
METRICS = {"clicks": "number", "impressions": "number", "prev_impressions": "number", "position": "number"}
SECTIONS = {
    "stage": {"current": ("integer_range", 0, 7), "note": nullable("string")},
    "next_action": {"who": enum("human", "agent"), "text": "string"},
    "asks": array({"title": "string", "waiting_for": nullable("string"), "since": "date"}),
    "sources": array({"name": "string", "state": enum("connected", "requested", "not_connected"), "note": nullable("string"), "checked_on": "date"}),
    "spend": array({"name": "string", "balance_usd": nullable("number"), "used_usd": nullable("number"), "checked_on": "date"}),
    "search": {
        "source": "string", "period": PERIOD, "prev_period": PERIOD,
        "totals": {"clicks": "number", "impressions": "number", "prev_clicks": nullable("number"), "prev_impressions": nullable("number"), "position": nullable("number"), "prev_position?": nullable("number")},
        "daily": array({"date": "date", "clicks": "number", "impressions": "number"}),
        "queries": array(dict(METRICS, query="string", brand="boolean")),
        "pages": array(dict(METRICS, page="string")), "note": "string",
    },
    "themes": array({"name": "string", "priority": enum("高", "中", "低")}),
    "keywords": array({
        "keyword": "string", "question?": "string", "theme": nullable("string"),
        "volume": nullable("number"), "recent3_avg": nullable("number"),
        "trend": enum("up", "flat", "down", "unknown"), "cpc_usd": nullable("number"),
        "competition": nullable(enum("LOW", "MEDIUM", "HIGH")),
        "ai_overview": nullable("boolean"), "own_cited": nullable("boolean"),
        "own_position": nullable("number"),
        "status": enum("candidate", "proposed", "approved", "briefed", "published", "dropped"),
        "rank": nullable("integer"), "reason": nullable("string"), "source": nullable("string"), "checked_on": "date",
    }),
    "citation_sources": {
        "checked_on": "date", "questions": "integer", "with_overview": nullable("integer"),
        "items": array({"domain": "string", "cited": "integer", "own": "boolean"}),
        "unknown?": nullable("integer"), "note?": nullable("string"),
    },
    "ai_visibility": {
        "panel": array({"id": "string", "question": "string"}),
        "log": array({"date": "date", "engine": "string", "question_id": "string", "cited": nullable("boolean"), "mentioned?": nullable("boolean"), "overview?": nullable("boolean"), "sources?": array("string")}),
    },
    "articles": array({"title": "string", "url": nullable("string"), "published_on": nullable("date"), "keyword": "string", "clicks": nullable("number"), "impressions": nullable("number"), "position": nullable("number"), "ai_cited": nullable("boolean"), "verdict": nullable(enum("効いている", "あと一歩", "別の問いで出ている", "出ていない", "まだ早い")), "state?": enum("brief", "draft", "in_review", "published")}),
    "readiness": {"checked_on": "date", "items": array({"level": enum("stop", "improve", "optional"), "title": "string", "state": enum("open", "done"), "note": nullable("string")})},
}


def valid_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        datetime.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def valid_timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?", value):
        return False
    if not valid_date(value[:10]):
        return False
    zone = re.search(r"([+-])(\d{2}):(\d{2})$", value)
    if zone and (int(zone[2]) > 23 or int(zone[3]) > 59):
        return False
    try:
        datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate(value, spec, path, errors):
    def fail(message):
        errors.append(f"{path}: {message}")

    if isinstance(spec, dict):
        if not isinstance(value, dict):
            fail("オブジェクトにしてください")
            return
        for field, child in spec.items():
            optional = field.endswith("?")
            key = field[:-1] if optional else field
            child_path = f"{path}.{key}" if path else key
            if key not in value:
                if not optional:
                    errors.append(f"{child_path}: 必須です")
            else:
                validate(value[key], child, child_path, errors)
        return
    if isinstance(spec, tuple):
        kind = spec[0]
        if kind == "nullable":
            if value is not None:
                validate(value, spec[1], path, errors)
        elif kind == "array":
            if not isinstance(value, list):
                fail("配列にしてください")
            else:
                for i, item in enumerate(value):
                    validate(item, spec[1], f"{path}[{i}]", errors)
        elif kind == "enum":
            if not isinstance(value, str) or value not in spec[1]:
                fail(" / ".join(spec[1]) + " のどれかにしてください")
        elif kind == "integer_range":
            if type(value) is not int or not spec[1] <= value <= spec[2]:
                fail(f"{spec[1]}〜{spec[2]} の整数にしてください")
        return
    if spec == "string" and not isinstance(value, str):
        fail("文字列にしてください")
    elif spec == "boolean" and type(value) is not bool:
        fail("true / false にしてください")
    elif spec == "integer" and type(value) is not int:
        fail("整数にしてください")
    elif spec == "number" and (type(value) not in (int, float) or (isinstance(value, float) and not math.isfinite(value))):
        fail("有限の数値にしてください")
    elif spec == "date" and not valid_date(value):
        fail("実在する日付を YYYY-MM-DD 形式にしてください")
    elif spec == "timestamp" and not valid_timestamp(value):
        fail("実在する日時を ISO 8601 形式にしてください")


def check(data):
    errors = []
    if not isinstance(data, dict):
        return ["データ: オブジェクトにしてください"]
    for key, spec in {"schema": "integer", "generated_at": "timestamp", "site": {"name": "string", "url": "string"}}.items():
        if key not in data:
            errors.append(f"{key}: 必須です")
        else:
            validate(data[key], spec, key, errors)
    if "schema" in data and (type(data["schema"]) is not int or data["schema"] != 1):
        if "schema: 整数にしてください" not in errors:
            errors.append("schema: 1 にしてください")
    for key, spec in SECTIONS.items():
        if key in data and data[key] is not None and data[key] != []:
            validate(data[key], spec, key, errors)
    return errors


def count(data, key):
    value = data.get(key)
    return len(value) if isinstance(value, list) else 0


def main():
    if sys.argv[1:] == ["--help"]:
        print("使い方: python3 check_data.py <file.json>\nSEO・AIO ダッシュボードのデータ形式を確認します。")
        return 0
    if len(sys.argv) != 2:
        print("使い方: python3 check_data.py <file.json>")
        return 1
    try:
        with open(sys.argv[1], encoding="utf-8") as file:
            data = json.load(file, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"{value} は JSON の数値ではありません")))
    except (OSError, ValueError) as error:
        print(f"ファイル: JSON を読み込めません（{error}）")
        return 1
    errors = check(data)
    if errors:
        print("\n".join(errors))
        return 1
    search = data.get("search") or {}
    visibility = data.get("ai_visibility") or {}
    print("OK")
    print(f"キーワード {count(data, 'keywords')} 件 / 日別 {count(search, 'daily')} 件 / 問い {count(search, 'queries')} 件 / ページ {count(search, 'pages')} 件 / AI の問い {count(visibility, 'panel')} 件 / AI 記録 {count(visibility, 'log')} 件 / 記事 {count(data, 'articles')} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
